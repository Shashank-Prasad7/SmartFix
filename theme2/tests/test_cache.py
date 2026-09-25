"""Unit tests for multi-tier cache and latency verification (Gate A3)."""
import tempfile
import time
from pathlib import Path

import pytest

import theme2.src.cache as cache_module
from theme2.src.cache import MultiTierCache, compute_article_hash
from theme2.src.normalizer import ComplaintNormalizer
from theme2.src.pipeline import TroubleshootingPipeline
from theme2.src.schema import SIISPayload


@pytest.fixture(scope="module")
def pipeline():
    return TroubleshootingPipeline.get_instance()


def test_cold_and_warm_repeat_latency(pipeline):
    import uuid
    uid = uuid.uuid4().hex[:6]
    query = f"My Galaxy S24 screen flickers and is very dark test {uid}"
    payload = SIISPayload(
        title=f"Screen flickering troubleshooting {uid}",
        content="## Check Display Settings\nOpen device Settings and navigate to Display. Check Adaptive brightness and screen timeout.\n## Restart Device\nPress and hold the Power button to reboot the phone."
    )

    # 1. Cold Call
    start_cold = time.perf_counter()
    resp_cold, meta_cold = pipeline.process(query, payload)
    cold_ms = (time.perf_counter() - start_cold) * 1000

    assert resp_cold is not None
    assert len(resp_cold.contexts) > 0
    assert meta_cold.get("X-Cache-Status") in ("miss", "procedure_hit")

    # 2. Warm Repeat Call (Must be <= 300ms, tested here typically < 10ms)
    start_warm = time.perf_counter()
    _, meta_warm = pipeline.process(query, payload)
    warm_ms = (time.perf_counter() - start_warm) * 1000

    assert meta_warm.get("X-Cache-Status") == "exact_hit"
    assert warm_ms <= 300.0, f"Repeat call took {warm_ms:.2f}ms, expected <= 300ms"
    print(f"\n[LATENCY TEST] Cold: {cold_ms:.2f}ms | Repeat Warm: {warm_ms:.2f}ms")


def test_paraphrase_cache_hit(pipeline):
    import uuid
    uid = uuid.uuid4().hex[:8]
    payload = SIISPayload(
        title=f"Screen flickering troubleshooting {uid}",
        content="## Check Display Settings\nOpen device Settings and navigate to Display. Check Adaptive brightness and screen timeout.\n## Restart Device\nPress and hold the Power button to reboot the phone."
    )
    seed = "My Galaxy S24 screen flickers and is very dark"
    pipeline.process(seed, payload)

    # Same source and compatible intent/facts are required for semantic reuse.
    paraphrase = "The screen on my Samsung S24 is flickering and dim"
    
    start_para = time.perf_counter()
    resp_para, meta_para = pipeline.process(paraphrase, payload)
    para_ms = (time.perf_counter() - start_para) * 1000

    assert resp_para is not None
    assert meta_para.get("X-Cache-Status") in ("semantic_hit", "exact_hit")
    assert para_ms <= 300.0, f"Paraphrase call took {para_ms:.2f}ms, expected <= 300ms"
    print(f"[PARAPHRASE TEST] Paraphrase Latency: {para_ms:.2f}ms | Cache Status: {meta_para.get('X-Cache-Status')}")

    changed_source = SIISPayload(title=payload.title, content=payload.content + "\nCheck the cable.")
    _, changed_meta = pipeline.process(paraphrase, changed_source)
    assert changed_meta["X-Cache-Status"] == "miss"


def test_operation_change_reuses_procedure_only(pipeline):
    import uuid
    payload = SIISPayload(
        title=f"Touch sensitivity {uuid.uuid4().hex[:8]}",
        content="## Touch sensitivity\nIf retaining a protector, enable Touch sensitivity in Settings.\nIf no film is used, disable Touch sensitivity in Settings.",
    )
    pipeline.process("Enable touch sensitivity", payload)
    _, metadata = pipeline.process("Disable touch sensitivity", payload)
    assert metadata["X-Cache-Status"] == "procedure_hit"


def test_restart_recovers_only_same_version_source_and_catalog():
    root = Path(__file__).resolve().parents[1]
    runtime = root / ".runtime"
    runtime.mkdir(exist_ok=True)
    source = SIISPayload(title="Restart persistence fixture", content="## Force restart\nPress Power for 20 seconds.")
    query = "My phone is frozen"
    pipeline = TroubleshootingPipeline.get_instance()
    response, _ = pipeline.process(query, source)
    article_hash = pipeline.article_hash(source)
    article = pipeline.cache.get_compiled_procedure(article_hash)
    assert article is not None
    with tempfile.TemporaryDirectory(prefix="restart-check-", dir=runtime) as directory:
        path = Path(directory) / "cache.sqlite3"
        first = MultiTierCache(path)
        first.store_procedure(article)
        first.store_answer(query, article_hash, ComplaintNormalizer.normalize(query), response)
        first.close()
        restarted = MultiTierCache(path)
        assert restarted.get_compiled_procedure(article_hash) == article
        assert restarted.get_exact_answer(query, article_hash) == response
        changed_source = compute_article_hash(source.title, source.content + "\nCheck cable.", f"{pipeline.resolver.catalog_digest}:{pipeline.resolver.index_version}")
        changed_catalog = compute_article_hash(source.title, source.content, "different-catalog")
        changed_version = compute_article_hash(source.title, source.content, f"{pipeline.resolver.catalog_digest}:{pipeline.resolver.index_version}", version="next-version")
        for incompatible_hash in (changed_source, changed_catalog, changed_version):
            assert restarted.get_compiled_procedure(incompatible_hash) is None
            assert restarted.get_exact_answer(query, incompatible_hash) is None
        restarted.close()


def test_semantic_hit_rescores_for_the_current_query():
    import uuid

    pipeline = TroubleshootingPipeline.get_instance()
    payload = SIISPayload(title=f"Screen flicker {uuid.uuid4().hex}", content="## Screen flicker\nPress Power for 20 seconds to restart.")
    first, _ = pipeline.process("My screen flickers", payload)
    second, metadata = pipeline.process("Please help my screen flickers", payload)
    assert metadata["X-Cache-Status"] == "semantic_hit"
    assert second.contexts[0].score != first.contexts[0].score


def test_cold_deadline_during_store_discards_both_artifacts(monkeypatch):
    import uuid

    pipeline = TroubleshootingPipeline.get_instance()
    payload = SIISPayload(title=f"Deadline cold {uuid.uuid4().hex}", content="## Restart\nPress Power for 20 seconds.")
    query = "My phone is frozen"
    article_hash = pipeline.article_hash(payload)
    deadline = time.perf_counter() + 0.9
    original_store = pipeline.cache.store_answer
    store_completed = []

    def slow_store(*args, **kwargs):
        original_store(*args, **kwargs)
        store_completed.append(True)
        time.sleep(max(0, deadline - 0.5 - time.perf_counter() + 0.02))

    monkeypatch.setattr(pipeline.cache, "store_answer", slow_store)
    with pytest.raises(TimeoutError, match="deadline"):
        pipeline.process(query, payload, deadline=deadline)
    assert store_completed
    assert pipeline.cache.get_exact_answer(query, article_hash) is None
    assert pipeline.cache.get_compiled_procedure(article_hash) is None


def test_semantic_deadline_during_store_preserves_seed_only(monkeypatch):
    import uuid

    pipeline = TroubleshootingPipeline.get_instance()
    payload = SIISPayload(title=f"Deadline semantic {uuid.uuid4().hex}", content="## Restart\nPress Power for 20 seconds.")
    seed = "My Galaxy S24 screen flickers and is very dark"
    paraphrase = "The screen on my Samsung S24 is flickering and dim"
    pipeline.process(seed, payload)
    article_hash = pipeline.article_hash(payload)
    deadline = time.perf_counter() + 0.9
    original_store = pipeline.cache.store_answer
    store_completed = []

    def slow_store(*args, **kwargs):
        original_store(*args, **kwargs)
        store_completed.append(True)
        time.sleep(max(0, deadline - 0.5 - time.perf_counter() + 0.02))

    monkeypatch.setattr(pipeline.cache, "store_answer", slow_store)
    with pytest.raises(TimeoutError, match="deadline"):
        pipeline.process(paraphrase, payload, deadline=deadline)
    assert store_completed
    assert pipeline.cache.get_exact_answer(seed, article_hash) is not None
    assert pipeline.cache.get_exact_answer(paraphrase, article_hash) is None
    assert pipeline.cache.get_compiled_procedure(article_hash) is not None


def test_corrupt_persisted_article_is_recompiled_from_current_source():
    import uuid

    pipeline = TroubleshootingPipeline.get_instance()
    payload = SIISPayload(title=f"Restart {uuid.uuid4().hex}", content="## Restart\nPress Power for 20 seconds.")
    article_hash = pipeline.article_hash(payload)
    article = pipeline.compiler.compile(payload.title, payload.content, article_hash)
    article.blocks[1].text = "Tampered instruction"
    pipeline.cache.store_procedure(article)
    response, metadata = pipeline.process("My device is frozen", payload)
    assert metadata["X-Cache-Status"] == "miss"
    assert "Tampered" not in response.model_dump_json()


def test_disk_eviction_keeps_newest_entries_under_same_second_writes(monkeypatch):
    monkeypatch.setattr(cache_module, "DISK_LIMIT", 3)
    root = Path(__file__).resolve().parents[1]
    runtime = root / ".runtime"
    runtime.mkdir(exist_ok=True)
    pipeline = TroubleshootingPipeline.get_instance()
    query = "My phone is frozen"
    response, _ = pipeline.process(query, SIISPayload(title="Eviction response", content="## Restart\nPress Power for 20 seconds."))
    normalized = ComplaintNormalizer.normalize(query)
    with tempfile.TemporaryDirectory(prefix="eviction-check-", dir=runtime) as directory:
        path = Path(directory) / "cache.sqlite3"
        cache = MultiTierCache(path)
        hashes = []
        for index in range(4):
            title = f"Eviction article {index}"
            content = "## Restart\nPress Power for 20 seconds."
            article_hash = compute_article_hash(title, content, "eviction-test")
            hashes.append(article_hash)
            cache.store_procedure(pipeline.compiler.compile(title, content, article_hash))
            cache.store_answer(f"{query} {index}", article_hash, normalized, response)
        cache.close()
        restarted = MultiTierCache(path)
        assert restarted.connection.execute("SELECT COUNT(*) FROM procedures").fetchone()[0] == 3
        assert restarted.connection.execute("SELECT COUNT(*) FROM answers").fetchone()[0] == 3
        assert restarted.get_compiled_procedure(hashes[0]) is None
        assert restarted.get_exact_answer(f"{query} 0", hashes[0]) is None
        for index in range(1, 4):
            assert restarted.get_compiled_procedure(hashes[index]) is not None
            assert restarted.get_exact_answer(f"{query} {index}", hashes[index]) is not None
        restarted.close()
