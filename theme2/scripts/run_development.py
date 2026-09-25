"""Fresh-cache executable checks for team-authored unfamiliar articles.

This produces contract and authored-fact evidence only, not independent
semantic judgments or live hosted/public latency measurements.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import runpy
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "data" / "fixtures" / "development_articles.json"
PAIRS = ROOT / "data" / "fixtures" / "development_fact_pairs.json"
SCHEMA = ROOT / "data" / "official" / "student_kit" / "schema.py"
QUERIES = {
    "DEV-FOLD-01": "The inner display is black but the cover screen works",
    "DEV-RADIO-02": "Disable Bluetooth scanning on my phone",
    "DEV-RESET-03": "How do I perform a factory data reset after backup?",
}


def main() -> int:
    run_id = f"development-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    db_path = ROOT / ".runtime" / f"{run_id}.sqlite3"
    os.environ["PRISM_CACHE_DB_PATH"] = str(db_path)

    from fastapi.testclient import TestClient

    from theme2.src.api import app
    from theme2.src.cache import PIPELINE_VERSION
    from theme2.src.pipeline import TroubleshootingPipeline
    from theme2.src.sanitizer import validate_response
    from theme2.src.schema import ContextDeeplinkResponse, SIISPayload

    official_model = runpy.run_path(str(SCHEMA))["ContextDeeplinkResponse"]
    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))["articles"]
    pairs = json.loads(PAIRS.read_text(encoding="utf-8"))["pairs"]
    by_id = {item["id"]: item for item in articles}
    client = TestClient(app)
    pipeline = TroubleshootingPipeline.get_instance()
    observations: list[dict[str, object]] = []
    failures: list[str] = []
    for item in articles:
        query = QUERIES[item["id"]]
        payload = {"query": query, "siis_response": {"title": item["title"], "content": item["content"]}}
        start = time.perf_counter()
        response = client.post("/v1/troubleshoot", json=payload)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        result = {"case_id": item["id"], "kind": "unfamiliar-team-authored-article", "http_status": response.status_code,
                  "cache_status": response.headers.get("X-Cache-Status"), "local_elapsed_ms": duration_ms,
                  "model_calls": 0, "contract_valid": False, "source_blocks_valid": False}
        if response.status_code == 200:
            try:
                body = response.json()
                parsed = ContextDeeplinkResponse.model_validate(body)
                official_model.model_validate(body)
                validate_response(parsed)
                pipeline.resolver.validate_response_links(parsed)
                source = SIISPayload(title=item["title"], content=item["content"])
                compiled = pipeline.cache.get_compiled_procedure(pipeline.article_hash(source))
                if compiled is None or not pipeline._article_matches_source(compiled, source, pipeline.article_hash(source)):
                    raise ValueError("Source block mismatch")
                result["contract_valid"] = True
                result["source_blocks_valid"] = True
                result["contexts"] = len(parsed.contexts)
                result["actions"] = sum(len(goal.actions) for goal in parsed.contexts)
            except ValueError as exc:
                failures.append(f"{item['id']}: {type(exc).__name__}")
        else:
            failures.append(f"{item['id']}: HTTP {response.status_code}")
        observations.append(result)
        print(f"{item['id']}: HTTP {response.status_code}, contract={result['contract_valid']}, cache={result['cache_status']}, local={duration_ms}ms")

    for pair in pairs:
        item = by_id[pair["article_id"]]
        statuses: list[str] = []
        for facts in (pair["base"], pair["changed"]):
            response = client.post("/v1/preview", json={"query": pair["query"], "siis_response": {"title": item["title"], "content": item["content"]}, "facts": facts})
            if response.status_code != 200:
                statuses.append(f"HTTP {response.status_code}")
                continue
            procedure = next(proc for proc in response.json()["preview"]["procedures"] if proc["title"] == pair["procedure_title"])
            statuses.append(procedure["actions"][pair["action_index"]]["applicability"])
        passed = statuses == pair["expected"]
        observations.append({"case_id": pair["id"], "kind": "team-authored-fact-pair", "observed": statuses,
                             "authored_expected": pair["expected"], "authored_assertion_pass": passed})
        if not passed:
            failures.append(f"{pair['id']}: authored fact assertion failed")
        print(f"{pair['id']}: {'PASS' if passed else 'FAIL'} {statuses}")

    report = ROOT / "reports" / run_id
    report.mkdir(parents=True, exist_ok=False)
    (report / "observations.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in observations), encoding="utf-8")
    metrics = {"articles": len(articles), "article_contract_pass": sum(row.get("contract_valid") is True for row in observations),
               "fact_pairs": len(pairs), "authored_fact_pair_pass": sum(row.get("authored_assertion_pass") is True for row in observations),
               "failures": failures, "scope": "team-authored development contract and fact assertions; no independent semantic labels"}
    (report / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    manifest = {"run_id": run_id, "article_fixture_sha256": hashlib.sha256(ARTICLES.read_bytes()).hexdigest(),
                "fact_pair_fixture_sha256": hashlib.sha256(PAIRS.read_bytes()).hexdigest(),
                "pipeline_version": PIPELINE_VERSION, "mode": "local deterministic fresh SQLite", "model_calls": 0,
                "python": platform.python_version(), "cache_database": db_path.name,
                "measurement_limit": "TestClient local elapsed time is not public or hosted latency"}
    (report / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"SUMMARY: article contract {metrics['article_contract_pass']}/{len(articles)}, authored fact pairs {metrics['authored_fact_pair_pass']}/{len(pairs)}; report={report}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
