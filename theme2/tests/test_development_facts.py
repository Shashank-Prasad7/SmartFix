"""Team-authored development fact-pair checks; reviewer labels remain pending."""

import json
from pathlib import Path

import pytest

from theme2.src.pipeline import TroubleshootingPipeline
from theme2.src.schema import SIISPayload

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = {item["id"]: item for item in json.loads((ROOT / "data" / "fixtures" / "development_articles.json").read_text(encoding="utf-8"))["articles"]}
PAIRS = json.loads((ROOT / "data" / "fixtures" / "development_fact_pairs.json").read_text(encoding="utf-8"))["pairs"]


@pytest.mark.parametrize("pair", PAIRS, ids=lambda pair: pair["id"])
def test_development_fact_pair_changes_only_supported_applicability(pair):
    item = ARTICLES[pair["article_id"]]
    payload = SIISPayload(title=item["title"], content=item["content"])
    pipeline = TroubleshootingPipeline.get_instance()
    pipeline.process(pair["query"], payload)
    observed = []
    for overrides in (pair["base"], pair["changed"]):
        projection = pipeline.preview(pair["query"], payload, overrides)["preview"]
        procedure = next(proc for proc in projection["procedures"] if proc["title"] == pair["procedure_title"])
        observed.append(procedure["actions"][pair["action_index"]]["applicability"])
    assert observed == pair["expected"]
