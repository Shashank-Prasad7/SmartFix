"""Offline official-input contract evaluation and submission export.

This verifies executable gates only. Semantic fidelity and live latency require
the independent annotations and public-endpoint protocol in EVAL.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import runpy
import sys
import time
import uuid
from pathlib import Path

from theme2.src.cache import DISK_LIMIT, HOT_LIMIT, PIPELINE_VERSION
from theme2.src.pipeline import TroubleshootingPipeline
from theme2.src.sanitizer import validate_response
from theme2.src.schema import ContextDeeplinkResponse, SIISPayload

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "official" / "student_kit" / "siis_responses.json"
OUTPUT = ROOT / "submission" / "results.jsonl"
OFFICIAL_MODEL = runpy.run_path(str(ROOT / "data" / "official" / "student_kit" / "schema.py"))["ContextDeeplinkResponse"]


def generate_paraphrases(query: str) -> list[str]:
    clean = re.sub(r"^\s*\d+[.)]\s*", "", query).strip().strip('"').rstrip(".?! ")
    return [
        f"How can I resolve this issue: {clean}?",
        f"Please walk me through fixing this: {clean}.",
        f"What troubleshooting steps apply when {clean.lower()}?",
        f"I need help with the following Samsung device problem: {clean}.",
        f"Which checks should I perform for this symptom: {clean}?",
        f"Can you explain a safe way to address this: {clean}?",
        f"My device has this problem: {clean}. What should I check first?",
        f"Give me guided steps for this situation: {clean}.",
        f"How do I diagnose and handle this: {clean}?",
    ]


def run_evaluation() -> int:
    if os.getenv("PRISM_LLM_MODE", "local").strip().lower() != "local":
        print("Offline contract export requires PRISM_LLM_MODE=local; hosted results need the live evaluation protocol.")
        return 2
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = data["responses"]
    run_id = f"offline-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    os.environ["PRISM_CACHE_DB_PATH"] = str(ROOT / ".runtime" / f"{run_id}.sqlite3")
    pipeline = TroubleshootingPipeline.get_instance()
    results: list[dict[str, object]] = []
    observations: list[dict[str, object]] = []
    failures: list[str] = []
    started = time.perf_counter()
    print(f"OFFLINE CONTRACT EVAL: {len(rows)} official queries")
    for index, row in enumerate(rows, 1):
        query = row["original_query"]
        payload = SIISPayload.model_validate(row["siis_response"])
        variations = generate_paraphrases(query)
        t0 = time.perf_counter()
        try:
            response, metadata = pipeline.process(query, payload)
            ContextDeeplinkResponse.model_validate(response.model_dump())
            OFFICIAL_MODEL.model_validate(response.model_dump())
            validate_response(response)
            pipeline.resolver.validate_response_links(response)
            if len(variations) != 9 or len({item.casefold() for item in variations}) != 9:
                raise ValueError("Variations are not nine unique strings")
            result = {"query": query, "query_variations": variations, "response": response.model_dump()}
            results.append(result)
            outcome = "PASS"
            contexts = len(response.contexts)
            actions = sum(len(goal.actions) for goal in response.contexts)
            cache_status = metadata["X-Cache-Status"]
        except (ValueError, OSError, TimeoutError) as exc:
            outcome = "FAIL"
            contexts = actions = 0
            cache_status = "none"
            failures.append(f"row {index}: {type(exc).__name__}: {exc}")
        duration_ms = (time.perf_counter() - t0) * 1000
        observations.append({"row": index, "outcome": outcome, "contexts": contexts, "actions": actions, "cache_status": cache_status, "duration_ms": round(duration_ms, 2)})
        print(f"{index:02d}/{len(rows):02d} {outcome} contexts={contexts} actions={actions} cache={cache_status} time={duration_ms:.2f}ms")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not failures:
        temporary = OUTPUT.with_suffix(".jsonl.tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            for result in results:
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
        catalog = json.loads((ROOT / "data" / "official" / "student_kit" / "deeplinks.json").read_text(encoding="utf-8"))["deeplinks"]
        approved_uris = {entry["deeplink"] for entry in catalog}
        approved_uris.add("bixby://dummy_positive")
        exported = [json.loads(line) for line in temporary.read_text(encoding="utf-8").splitlines()]
        if len(exported) != len(rows):
            raise ValueError("Submission export row count changed")
        for source_row, exported_row in zip(rows, exported, strict=True):
            if exported_row["query"] != source_row["original_query"] or len(exported_row["query_variations"]) != 9:
                raise ValueError("Submission export query or variation mismatch")
            response = ContextDeeplinkResponse.model_validate(exported_row["response"])
            OFFICIAL_MODEL.model_validate(exported_row["response"])
            validate_response(response)
            pipeline.resolver.validate_response_links(response)
            for goal in response.contexts:
                for action in goal.actions:
                    for group in action.stepGroups:
                        if group.actionableDeeplink and group.actionableDeeplink.deeplink not in approved_uris:
                            raise ValueError("Submission contains unapproved actionable URI")
        temporary.replace(OUTPUT)
    run_dir = ROOT / "reports" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "observations.jsonl").write_text("".join(json.dumps(item) + "\n" for item in observations), encoding="utf-8")
    metrics = {
        "dataset": "official-20", "total": len(rows), "passed": len(results), "failed": len(failures),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "failures": failures,
        "scope": "offline executable contract and coverage checks only; semantic accuracy and public latency not measured",
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    manifest = {
        "run_id": run_id, "dataset_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "catalog_sha256": pipeline.resolver.catalog_digest, "pipeline_version": PIPELINE_VERSION,
        "output_policy": "full-source", "mode": "deterministic offline",
        "model_ids": None, "provider_calls": 0, "cost": None,
        "python": platform.python_version(), "cache_hot_limit": HOT_LIMIT,
        "cache_disk_limit_per_table": DISK_LIMIT, "cache_database": Path(os.environ["PRISM_CACHE_DB_PATH"]).name,
        "paraphrase_policy": "nine deterministic generated variants per query; human review pending",
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"SUMMARY: {len(results)}/{len(rows)} passed; {len(failures)} failed; export={OUTPUT if not failures else 'not written'}")
    print(f"EVIDENCE: {run_dir}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(run_evaluation())
