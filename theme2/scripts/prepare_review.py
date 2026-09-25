"""Prepare blind, source-first reviewer sheets without candidate outputs.

Never overwrite a filled review pack. Run with --check to verify generated
materials still match the current official and development inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from theme2.tests.run_eval import generate_paraphrases

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "data" / "official" / "student_kit" / "siis_responses.json"
ARTICLES = ROOT / "data" / "fixtures" / "development_articles.json"
PAIRS = ROOT / "data" / "fixtures" / "development_fact_pairs.json"
ADVERSARIES = ROOT / "data" / "fixtures" / "cache_adversaries.json"
OUTPUT = ROOT / "data" / "annotations" / "review_pack"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_jsonl(rows: list[dict[str, object]]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def prepare() -> dict[str, str]:
    official = json.loads(OFFICIAL.read_text(encoding="utf-8"))["responses"]
    development = json.loads(ARTICLES.read_text(encoding="utf-8"))["articles"]
    pairs = json.loads(PAIRS.read_text(encoding="utf-8"))["pairs"]
    adversaries = json.loads(ADVERSARIES.read_text(encoding="utf-8"))["cases"]
    unique: dict[str, dict[str, object]] = {}
    article_ids: dict[int, str] = {}
    for index, row in enumerate(official, 1):
        source = row["siis_response"]
        source_hash = digest(json.dumps(source, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        if source_hash not in unique:
            article_id = f"OFF-ART-{len(unique)+1:02d}"
            unique[source_hash] = {
                "case_id": article_id, "split": "public-development", "provenance": "supplied SIIS article",
                "source_sha256": source_hash, "title": source["title"], "content": source["content"],
            }
        article_ids[index] = str(unique[source_hash]["case_id"])
    article_rows = list(unique.values()) + [
        {
            "case_id": item["id"], "split": "team-authored-development",
            "provenance": "synthetic fixture", "source_sha256": digest(json.dumps({"title": item["title"], "content": item["content"]}, sort_keys=True, ensure_ascii=False).encode("utf-8")),
            "title": item["title"], "content": item["content"],
        }
        for item in development
    ]
    queries = [
        {
            "case_id": f"OFF-Q-{index:02d}", "article_id": article_ids[index],
            "query": row["original_query"], "split": "public-development",
            "relevant_procedure_inventory": None, "off_topic_procedure_ids": None,
            "applicability_decisions": None, "reviewer_notes": None,
        }
        for index, row in enumerate(official, 1)
    ]
    article_sheets = [
        {
            **row, "full_source_action_inventory": None,
            "required_instruction_units": None, "warnings_and_conditions": None,
            "prerequisite_order": None, "alternative_groups": None,
            "catalog_setting_operation_ids": None, "uncertain_items": None,
            "reviewer_notes": None,
        }
        for row in article_rows
    ]
    fact_sheets = [
        {
            "case_id": item["id"], "article_id": item["article_id"],
            "query": item["query"], "base_facts": item["base"],
            "changed_facts": item["changed"], "split": "team-authored-development",
            "base_applicability_labels": None, "changed_applicability_labels": None,
            "reviewer_notes": None,
        }
        for item in pairs
    ]
    variations = [
        {
            "case_id": f"OFF-Q-{index:02d}-V{variant_index:02d}",
            "canonical_query": row["original_query"], "variation": variation,
            "same_intent_and_facts": None, "diversity_ok": None, "reviewer_notes": None,
        }
        for index, row in enumerate(official, 1)
        for variant_index, variation in enumerate(generate_paraphrases(row["original_query"]), 1)
    ]
    manifest = {
        "purpose": "Blind independent semantic review before candidate outputs are shown",
        "official_dataset_sha256": digest(OFFICIAL.read_bytes()),
        "development_articles_sha256": digest(ARTICLES.read_bytes()),
        "development_fact_pairs_sha256": digest(PAIRS.read_bytes()),
        "cache_adversaries_sha256": digest(ADVERSARIES.read_bytes()),
        "counts": {"official_queries": len(official), "unique_official_articles": len(unique),
                   "development_articles": len(development), "development_fact_pairs": len(pairs),
                   "development_cache_adversaries": len(adversaries), "variations": len(variations)},
        "sealed_holdout": {
            "article_slots": ["HOLD-ART-01", "HOLD-ART-02", "HOLD-ART-03"],
            "fact_pair_slots": [f"HOLD-FACT-{index:02d}" for index in range(1, 7)],
            "status": "PENDING independent source/label supply; no holdout content in this pack",
        },
    }
    files = {"manifest.json": json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"}
    for reviewer in ("A", "B"):
        files[f"reviewer_{reviewer}_articles.jsonl"] = render_jsonl(article_sheets)
        files[f"reviewer_{reviewer}_queries.jsonl"] = render_jsonl(queries)
        files[f"reviewer_{reviewer}_fact_pairs.jsonl"] = render_jsonl(fact_sheets)
        files[f"reviewer_{reviewer}_variations.jsonl"] = render_jsonl(variations)
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Compare existing files without editing them")
    args = parser.parse_args()
    files = prepare()
    if args.check:
        mismatches = [name for name, body in files.items() if not (OUTPUT / name).is_file() or (OUTPUT / name).read_text(encoding="utf-8") != body]
        print(f"REVIEW PACK: {len(files)-len(mismatches)}/{len(files)} files match current inputs")
        if mismatches:
            print("MISMATCH: " + ", ".join(mismatches))
        return 1 if mismatches else 0
    OUTPUT.mkdir(parents=True, exist_ok=True)
    existing = [name for name in files if (OUTPUT / name).exists()]
    if existing:
        raise FileExistsError("Review pack exists; use --check and preserve reviewer work")
    for name, body in files.items():
        (OUTPUT / name).write_text(body, encoding="utf-8", newline="\n")
    print(f"REVIEW PACK: wrote {len(files)} files to {OUTPUT}")
    print(json.dumps(json.loads(files["manifest.json"])["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
