"""Hosted stages use model output only after source and cache checks."""

import uuid

import pytest

from theme2.src.hosted_llm import GeminiTwoStage
from theme2.src.normalizer import ComplaintNormalizer
from theme2.src.pipeline import TroubleshootingPipeline
from theme2.src.schema import SIISPayload


def _adapter() -> GeminiTwoStage:
    return GeminiTwoStage("test-key", "gemini-3.1-flash-lite", "gemini-3.8-flash")


def test_hosted_normalization_changes_search_text_but_not_explicit_facts(monkeypatch):
    adapter = _adapter()
    query = "Keep my protector and enable touch sensitivity"
    baseline = ComplaintNormalizer.normalize(query)
    monkeypatch.setattr(adapter, "_generate", lambda *_: {"technical_query": "enable touch sensitivity with retained screen protector"})
    normalized = adapter.normalize(query, baseline, float("inf"))
    assert normalized.technical_query != query
    assert normalized.compatibility_key() == baseline.compatibility_key()
    assert normalized.facts == baseline.facts


def test_hosted_structure_accepts_complete_order_and_rejects_invented_step(monkeypatch):
    adapter = _adapter()
    pipeline = TroubleshootingPipeline(hosted=adapter)
    payload = SIISPayload(title="Restart and inspect", content="## Restart device\nPress the Power button to restart.\n## Inspect display\nCheck the screen for damage.")
    article = pipeline.compiler.compile(payload.title, payload.content, pipeline.article_hash(payload))
    proposal = {"procedures": [
        {"id": procedure.id, "actions": [{"id": action.id, "steps": action.steps} for action in procedure.actions]}
        for procedure in reversed(article.procedures)
    ]}
    monkeypatch.setattr(adapter, "_generate", lambda *_: proposal)
    structured = adapter.structure(article, float("inf"))
    assert [item.id for item in structured.procedures] == [item.id for item in reversed(article.procedures)]
    assert structured.ledger == article.ledger
    proposal["procedures"][0]["actions"][0]["steps"] = ["Delete all photos."]
    with pytest.raises(ValueError, match="differs from source"):
        adapter.structure(article, float("inf"))


def test_hosted_structure_keeps_destructive_procedure_after_prior_checks(monkeypatch):
    adapter = _adapter()
    pipeline = TroubleshootingPipeline(hosted=adapter)
    payload = SIISPayload(
        title="Reset device",
        content="## Inspect device\nCheck the charging cable.\n## Factory data reset\nBack up personal data before proceeding. Tap Factory data reset in Settings. This erases all data.",
    )
    article = pipeline.compiler.compile(payload.title, payload.content, pipeline.article_hash(payload))
    assert len(article.procedures) == 2
    assert any(action.category == "critical" for action in article.procedures[1].actions)
    proposal = {"procedures": [
        {"id": procedure.id, "actions": [{"id": action.id, "steps": action.steps} for action in procedure.actions]}
        for procedure in reversed(article.procedures)
    ]}
    monkeypatch.setattr(adapter, "_generate", lambda *_: proposal)
    with pytest.raises(ValueError, match="Critical procedure moved"):
        adapter.structure(article, float("inf"))


def test_pipeline_calls_two_stages_only_for_cold_hosted_request():
    class FakeHosted:
        cache_identity = "fake-two-stage-v1"

        def __init__(self):
            self.calls = []

        def normalize(self, query, baseline, deadline):
            self.calls.append("normalize")
            return baseline.model_copy(update={"technical_query": "touch sensitivity setting"})

        def structure(self, article, deadline):
            self.calls.append("structure")
            return article

    hosted = FakeHosted()
    pipeline = TroubleshootingPipeline(hosted=hosted)
    payload = SIISPayload(
        title=f"Touch sensitivity {uuid.uuid4().hex}",
        content="## Touch sensitivity\nIf retaining a protector, enable Touch sensitivity in Settings.\nIf no film is used, disable Touch sensitivity in Settings.",
    )
    _, cold = pipeline.process("Enable touch sensitivity", payload)
    assert cold["X-Cache-Status"] == "miss"
    assert cold["X-Hosted-Calls"] == "2"
    assert hosted.calls == ["normalize", "structure"]
    _, exact = pipeline.process("Enable touch sensitivity", payload)
    assert exact["X-Cache-Status"] == "exact_hit"
    assert exact["X-Hosted-Calls"] == "0"
    _, reused = pipeline.process("Disable touch sensitivity", payload)
    assert reused["X-Cache-Status"] == "procedure_hit"
    assert reused["X-Hosted-Calls"] == "1"
    assert hosted.calls == ["normalize", "structure", "normalize"]


def test_hosted_mode_requires_api_key(monkeypatch):
    monkeypatch.setenv("PRISM_LLM_MODE", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiTwoStage.from_environment()
