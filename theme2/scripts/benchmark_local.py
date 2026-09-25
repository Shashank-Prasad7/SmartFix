"""Reproducible loopback benchmark with isolated empty caches.

This is a local deterministic-workload diagnostic, not public or hosted-model
latency evidence. It never sends the official kit to an external host.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from theme2.src.cache import DISK_LIMIT, HOT_LIMIT, PIPELINE_VERSION
from theme2.tests.run_eval import generate_paraphrases

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[math.ceil(fraction * len(ordered)) - 1], 2)


def call(base_url: str, query: str, source: dict[str, str]) -> tuple[int, str, float]:
    request = urllib.request.Request(
        base_url + "/v1/troubleshoot",
        data=json.dumps({"query": query, "siis_response": source}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=8.5) as response:
            response.read()
            return response.status, response.headers.get("X-Cache-Status", "missing"), (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as error:
        error.read()
        return error.code, "error", (time.perf_counter() - started) * 1000


def main() -> int:
    run_id = f"loopback-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    run_dir = ROOT / "reports" / run_id
    run_dir.mkdir(parents=True)
    db_path = ROOT / ".runtime" / f"{run_id}.sqlite3"
    env = dict(os.environ, PRISM_CACHE_DB_PATH=str(db_path))
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    service = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "theme2.src.api:app", "--host", "127.0.0.1", "--port", str(port), "--workers", "1"],
        cwd=REPO, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        startup = time.perf_counter()
        while time.perf_counter() - startup < 12:
            if service.poll() is not None:
                raise RuntimeError("Service failed to start")
            try:
                with urllib.request.urlopen(base_url + "/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        else:
            raise TimeoutError("Service readiness timed out")
        startup_ms = round((time.perf_counter() - startup) * 1000, 2)
        rows = json.loads((ROOT / "data" / "official" / "student_kit" / "siis_responses.json").read_text(encoding="utf-8"))["responses"]
        observations: list[dict[str, object]] = []
        variations = [generate_paraphrases(row["original_query"]) for row in rows]
        workloads = (
            [("seed", index, row["original_query"], row["siis_response"]) for index, row in enumerate(rows)],
            [("exact", repetition, rows[repetition % 20]["original_query"], rows[repetition % 20]["siis_response"]) for repetition in range(250)],
            [("paraphrase_first", index * 9 + variation, query, row["siis_response"]) for index, row in enumerate(rows) for variation, query in enumerate(variations[index])],
            [("paraphrase_repeat", index * 9 + variation, variations[index][variation], row["siis_response"])
             for index, row in enumerate(rows) for variation in range(4 if index < 10 else 3)],
        )
        for workload in workloads:
            for kind, case, query, source in workload:
                status, cache, duration = call(base_url, query, source)
                observations.append({"kind": kind, "case": case, "http_status": status, "cache_status": cache, "public_loopback_ms": round(duration, 2)})
        metrics: dict[str, object] = {"scope": "local loopback, deterministic offline backend, fresh isolated SQLite; not hosted-model or external-network evidence", "startup_ms": startup_ms, "workloads": {}}
        for kind in ("seed", "exact", "paraphrase_first", "paraphrase_repeat", "cached_500"):
            subset = [item for item in observations if item["kind"] == kind] if kind != "cached_500" else [item for item in observations if item["kind"] != "seed"]
            successful = [float(item["public_loopback_ms"]) for item in subset if item["http_status"] == 200]
            answer_hits = sum(item["cache_status"] in {"exact_hit", "semantic_hit"} for item in subset)
            metrics["workloads"][kind] = {"attempts": len(subset), "successes": len(successful), "answer_hits": answer_hits, "answer_hit_rate": round(answer_hits / len(subset), 4), "p50_ms": percentile(successful, 0.5), "p95_ms": percentile(successful, 0.95), "max_ms": round(max(successful), 2) if successful else None}
        (run_dir / "observations.jsonl").write_text("".join(json.dumps(item) + "\n" for item in observations), encoding="utf-8")
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        manifest = {
            "run_id": run_id, "dataset_sha256": hashlib.sha256((ROOT / "data" / "official" / "student_kit" / "siis_responses.json").read_bytes()).hexdigest(),
            "catalog_sha256": hashlib.sha256((ROOT / "data" / "official" / "student_kit" / "deeplinks.json").read_bytes()).hexdigest(),
            "pipeline_version": PIPELINE_VERSION, "output_policy": "full-source",
            "environment": "local Windows loopback", "python": platform.python_version(),
            "cache_hot_limit": HOT_LIMIT, "cache_disk_limit_per_table": DISK_LIMIT,
            "cache_database": db_path.name, "model_ids": None, "provider_calls": 0,
            "cost": None, "quantile": "nearest-rank", "paraphrase_source": "generated templates; 180 first exposures and 70 labeled repeats for latency only",
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        for kind, item in metrics["workloads"].items():
            print(f"{kind}: {item['successes']}/{item['attempts']} success; answer hits {item['answer_hits']}/{item['attempts']}; p95 {item['p95_ms']} ms")
        print(f"EVIDENCE: {run_dir}")
        return 0 if all(item["http_status"] == 200 for item in observations) else 1
    finally:
        service.terminate()
        try:
            service.wait(timeout=5)
        except subprocess.TimeoutExpired:
            service.kill()
            service.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
