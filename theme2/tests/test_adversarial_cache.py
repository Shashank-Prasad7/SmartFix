"""Team-authored development adversaries; no independent semantic labels."""

import json
import uuid
from pathlib import Path

import pytest

from theme2.src.normalizer import ComplaintNormalizer
from theme2.src.pipeline import TroubleshootingPipeline
from theme2.src.schema import SIISPayload

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "data" / "fixtures" / "cache_adversaries.json").read_text(encoding="utf-8"))
CASES = FIXTURE["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_changed_intent_fact_or_reference_cannot_reuse_an_answer(case):
    assert ComplaintNormalizer.normalize(case["seed"]).compatibility_key() != ComplaintNormalizer.normalize(case["changed"]).compatibility_key()
    payload = SIISPayload(
        title=f"Development cache sentinel {case['id']} {uuid.uuid4().hex}",
        content="## Radio check\nDisable Bluetooth in Settings.\n## Manual check\nPress the side key to restart the device.",
    )
    pipeline = TroubleshootingPipeline.get_instance()
    _, seed_meta = pipeline.process(case["seed"], payload)
    _, changed_meta = pipeline.process(case["changed"], payload)
    assert seed_meta["X-Cache-Status"] == "miss"
    assert changed_meta["X-Cache-Status"] == "procedure_hit"
