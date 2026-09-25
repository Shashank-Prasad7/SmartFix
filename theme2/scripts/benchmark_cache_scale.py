"""Measure a 10,000-entry synthetic SQLite answer-cache workload.

This checks bounded lookup/storage behavior only. It does not test semantic
correctness, hosted inference, public latency, or 10,000 source scenarios.
"""

from __future__ import annotations

import json
import math
import statistics
import tempfile
import time
import uuid
from pathlib import Path

from theme2.src.cache import DISK_LIMIT, HOT_LIMIT, MultiTierCache, compute_article_hash
from theme2.src.normalizer import ComplaintNormalizer
from theme2.src.pipeline import TroubleshootingPipeline
from theme2.src.schema import SIISPayload

ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return round(ordered[math.ceil(fraction * len(ordered)) - 1], 3)


def main() -> int:
    run_id = f"cache-scale-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    report = ROOT / "reports" / run_id
    report.mkdir(parents=True, exist_ok=False)
    payload = SIISPayload(title="Synthetic cache scale setup", content="## Restart\nPress Power for 20 seconds.")
    response, _ = TroubleshootingPipeline.get_instance().process("My phone is frozen", payload)
    article_hash = compute_article_hash("Synthetic cache article", "Synthetic lookup keys", "scale-only")
    normalized = ComplaintNormalizer.normalize("My phone is frozen")
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    count = 10_000
    queries = [f"synthetic cache key {index:05d}" for index in range(count + 1)]
    with tempfile.TemporaryDirectory(prefix="cache-scale-", dir=runtime) as directory:
        db_path = Path(directory) / "cache.sqlite3"
        cache = MultiTierCache(db_path)
        write_started = time.perf_counter()
        for query in queries:
            cache.store_answer(query, article_hash, normalized, response)
        write_ms = round((time.perf_counter() - write_started) * 1000, 2)
        hot_count = len(cache.hot_answers)
        disk_count = cache.connection.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        db_bytes = db_path.stat().st_size
        cache.close()
        restarted = MultiTierCache(db_path)
        evicted_oldest = restarted.get_exact_answer(queries[0], article_hash) is None
        newest_present = restarted.get_exact_answer(queries[-1], article_hash) is not None
        samples: list[float] = []
        misses = 0
        for index in range(1, count + 1, 50):
            started = time.perf_counter()
            value = restarted.get_exact_answer(queries[index], article_hash)
            samples.append((time.perf_counter() - started) * 1000)
            misses += value is None
        restarted.close()
    result = {
        "run_id": run_id,
        "scope": "synthetic 10,001 key writes to a 10,000-entry bounded answer cache; single process; no semantic claim",
        "write_count": len(queries), "write_total_ms": write_ms,
        "disk_limit": DISK_LIMIT, "disk_count": disk_count, "hot_limit": HOT_LIMIT, "hot_count": hot_count,
        "db_bytes_before_cleanup": db_bytes,
        "oldest_evicted_after_restart": evicted_oldest, "newest_present_after_restart": newest_present,
        "lookup_count": len(samples), "lookup_misses": misses,
        "lookup_p50_ms": round(statistics.median(samples), 3), "lookup_p95_ms": percentile(samples, 0.95),
        "lookup_max_ms": round(max(samples), 3),
        "limits": "No hosted calls, public network, concurrency, or semantic answer evaluation",
    }
    (report / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    passed = disk_count == DISK_LIMIT and hot_count <= HOT_LIMIT and evicted_oldest and newest_present and misses == 0
    print(f"CACHE SCALE: {'PASS' if passed else 'FAIL'}; writes={len(queries)}, disk={disk_count}/{DISK_LIMIT}, hot={hot_count}/{HOT_LIMIT}")
    print(f"LOOKUP: {len(samples)-misses}/{len(samples)} hits, p50={result['lookup_p50_ms']}ms, p95={result['lookup_p95_ms']}ms, max={result['lookup_max_ms']}ms")
    print(f"EVIDENCE: {report}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
