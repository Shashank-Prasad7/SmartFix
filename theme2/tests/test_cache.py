"""Unit tests for multi-tier cache and latency verification (Gate A3)."""
import time
import pytest
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
    resp_warm, meta_warm = pipeline.process(query, payload)
    warm_ms = (time.perf_counter() - start_warm) * 1000

    assert meta_warm.get("X-Cache-Status") == "exact_hit"
    assert warm_ms <= 300.0, f"Repeat call took {warm_ms:.2f}ms, expected <= 300ms"
    print(f"\n[LATENCY TEST] Cold: {cold_ms:.2f}ms | Repeat Warm: {warm_ms:.2f}ms")


def test_paraphrase_cache_hit(pipeline):
    payload = SIISPayload(
        title="Screen flickering troubleshooting",
        content="## Check Display Settings\nOpen device Settings and navigate to Display. Check Adaptive brightness and screen timeout.\n## Restart Device\nPress and hold the Power button to reboot the phone."
    )
    
    # Paraphrase of "My Galaxy S24 screen flickers and is very dark"
    paraphrase = "The screen on my Samsung S24 is flickering and dim"
    
    start_para = time.perf_counter()
    resp_para, meta_para = pipeline.process(paraphrase, payload)
    para_ms = (time.perf_counter() - start_para) * 1000

    assert resp_para is not None
    assert meta_para.get("X-Cache-Status") in ("semantic_hit", "exact_hit")
    assert para_ms <= 300.0, f"Paraphrase call took {para_ms:.2f}ms, expected <= 300ms"
    print(f"[PARAPHRASE TEST] Paraphrase Latency: {para_ms:.2f}ms | Cache Status: {meta_para.get('X-Cache-Status')}")
