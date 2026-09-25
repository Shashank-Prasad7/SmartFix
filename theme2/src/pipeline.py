"""Source-grounded request pipeline and stateless diagnostic projection."""

from __future__ import annotations

import json
import re
import time
from threading import Lock, RLock

from theme2.src.cache import MultiTierCache, compute_article_hash
from theme2.src.compiler import DUMMY_CATALOG_ID, SIISCompiler
from theme2.src.deeplink_resolver import DeeplinkResolver, tokens
from theme2.src.hosted_llm import GeminiTwoStage
from theme2.src.normalizer import ComplaintNormalizer, NormalizedComplaint
from theme2.src.records import CompiledArticle
from theme2.src.sanitizer import (
    create_dummy_deeplink,
    enforce_description_format,
    enforce_goal_format,
    enforce_title_word_count,
    sanitize_response,
    sanitize_text,
    validate_response,
)
from theme2.src.schema import (
    Action,
    ContextDeeplinkResponse,
    Goal,
    SIISPayload,
    StepGroup,
    actionCategory,
)


class AdmissionRejected(RuntimeError):
    """Configured inference capacity or quota rejected the request."""


class TroubleshootingPipeline:
    _instance: TroubleshootingPipeline | None = None
    _instance_lock = Lock()

    def __init__(self, hosted: GeminiTwoStage | None = None) -> None:
        self.resolver = DeeplinkResolver.get_instance()
        self.normalizer = ComplaintNormalizer.get_instance()
        self.compiler = SIISCompiler.get_instance()
        self.cache = MultiTierCache.get_instance()
        self.hosted = hosted if hosted is not None else GeminiTwoStage.from_environment()
        self._article_locks = [RLock() for _ in range(64)]

    @classmethod
    def get_instance(cls) -> TroubleshootingPipeline:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def article_hash(self, payload: SIISPayload) -> str:
        mode = self.hosted.cache_identity if self.hosted else "local"
        return compute_article_hash(payload.title, payload.content, f"{self.resolver.catalog_digest}:{self.resolver.index_version}:{mode}")

    @staticmethod
    def _description(name: str, category: actionCategory) -> str:
        lower = name.lower().strip()
        if "back up" in lower or "backup" in lower:
            return "It will help preserve your data"
        if category == actionCategory.critical:
            return "It will explain the critical procedure"
        if re.match(r"^(?:check|open|restart|connect|contact|use|inspect|enable|disable|update|remove)\b", lower):
            return enforce_description_format(f"help you {lower}")
        if len(lower.split()) <= 4 and not lower.startswith(("some ", "device ")):
            return enforce_description_format(f"explain {lower}")
        return "It will guide this troubleshooting procedure"

    def _render(self, article: CompiledArticle, complaint: NormalizedComplaint) -> ContextDeeplinkResponse:
        query_terms = set(tokens(complaint.technical_query))
        contexts: list[Goal] = []
        for procedure in article.procedures:
            topic = enforce_title_word_count(procedure.title, "Device Procedure")
            title = sanitize_text(topic)
            goal = enforce_goal_format("", title)
            guide_actions: list[Action] = []
            for source_action in procedure.actions:
                link = validation = None
                if source_action.catalog_id:
                    if source_action.catalog_id == DUMMY_CATALOG_ID:
                        if source_action.operation != "open" or not source_action.setting:
                            raise ValueError("Invalid dummy mapping")
                        link = create_dummy_deeplink(source_action.setting)
                    else:
                        entry = self.resolver.by_id.get(source_action.catalog_id)
                        if entry is None or self.resolver._operation(entry) != source_action.operation:
                            raise ValueError("Stale or incompatible catalog mapping")
                        link, validation = self.resolver.materialize(source_action.catalog_id)
                category = actionCategory(source_action.category)
                if category == actionCategory.auto and link is None:
                    raise ValueError("Automatic action without approved link")
                guide_actions.append(Action(
                    actionName=sanitize_text(source_action.name),
                    description=self._description(source_action.name, category),
                    category=category,
                    stepGroups=[StepGroup(
                        steps=[sanitize_text(step) for step in source_action.steps],
                        actionableDeeplink=link, validationDeeplink=validation,
                    )],
                ))
            source_terms = set(tokens(procedure.title + " " + " ".join(action.name for action in procedure.actions)))
            score = len(query_terms & source_terms) / max(1, len(query_terms | source_terms))
            contexts.append(Goal(goal=goal, title=title, score=max(0.0, min(1.0, score)), actions=guide_actions))
        response = sanitize_response(ContextDeeplinkResponse(contexts=contexts))
        validate_response(response)
        self.resolver.validate_response_links(response)
        return response

    @staticmethod
    def _rescore_cached_response(response: ContextDeeplinkResponse, complaint: NormalizedComplaint) -> None:
        query_terms = set(tokens(complaint.technical_query))
        for goal in response.contexts:
            source_terms = set(tokens(goal.title + " " + " ".join(action.actionName for action in goal.actions)))
            goal.score = len(query_terms & source_terms) / max(1, len(query_terms | source_terms))

    @staticmethod
    def _article_matches_source(article: CompiledArticle, payload: SIISPayload, article_hash: str) -> bool:
        return (
            article.article_hash == article_hash
            and article.title == payload.title
            and all(0 <= block.start < block.end <= len(payload.content) and payload.content[block.start:block.end] == block.text for block in article.blocks)
        )

    def process(self, query: str, siis_payload: SIISPayload, deadline: float | None = None) -> tuple[ContextDeeplinkResponse, dict[str, str]]:
        started = time.perf_counter()
        deadline = started + 7.5 if deadline is None else deadline
        completion_deadline = deadline - 0.5
        if not query.strip() or not siis_payload.content.strip():
            raise ValueError("Blank query or source content")
        stages: dict[str, float] = {}
        hosted_calls = 0
        stage_started = time.perf_counter()
        article_hash = self.article_hash(siis_payload)
        stages["source_identity"] = round((time.perf_counter() - stage_started) * 1000, 2)

        def metadata(status: str, **extra: str) -> dict[str, str]:
            return {"X-Cache-Status": status, "X-Processing-Time-Ms": f"{(time.perf_counter()-started)*1000:.2f}",
                    "X-Stage-Timings-Json": json.dumps(stages, sort_keys=True),
                    "X-Hosted-Calls": str(hosted_calls),
                    "X-LLM-Mode": "gemini" if self.hosted else "local", **extra}

        article_lock = self._article_locks[int(article_hash[:8], 16) % len(self._article_locks)]
        lock_started = time.perf_counter()
        with article_lock:  # Coalesces identical source misses without serializing unrelated articles.
            stages["article_lock_wait"] = round((time.perf_counter() - lock_started) * 1000, 2)
            if time.perf_counter() >= completion_deadline:
                raise TimeoutError("Application deadline exceeded")
            stage_started = time.perf_counter()
            exact = self.cache.get_exact_answer(query, article_hash)
            stages["exact_lookup"] = round((time.perf_counter() - stage_started) * 1000, 2)
            if exact is not None:
                try:
                    validate_response(exact)
                    self.resolver.validate_response_links(exact)
                    if time.perf_counter() >= completion_deadline:
                        raise TimeoutError("Application deadline exceeded")
                    return exact, metadata("exact_hit")
                except ValueError:
                    pass

            stage_started = time.perf_counter()
            complaint = self.normalizer.normalize(query)
            if self.hosted is not None:
                hosted_calls += 1
                complaint = self.hosted.normalize(query, complaint, completion_deadline)
            stages["normalization"] = round((time.perf_counter() - stage_started) * 1000, 2)
            stage_started = time.perf_counter()
            semantic = self.cache.get_semantic_answer(query, article_hash, complaint)
            stages["semantic_lookup"] = round((time.perf_counter() - stage_started) * 1000, 2)
            if semantic is not None:
                response, similarity, _matched_query = semantic
                try:
                    self._rescore_cached_response(response, complaint)
                    validate_response(response)
                    self.resolver.validate_response_links(response)
                    stage_started = time.perf_counter()
                    if time.perf_counter() >= completion_deadline:
                        raise TimeoutError("Application deadline exceeded")
                    try:
                        self.cache.store_answer(query, article_hash, complaint, response)
                    except Exception:
                        self.cache.discard_attempt(query, article_hash, new_procedure=False)
                        raise
                    if time.perf_counter() >= completion_deadline:
                        self.cache.discard_attempt(query, article_hash, new_procedure=False)
                        raise TimeoutError("Application deadline exceeded")
                    stages["answer_store"] = round((time.perf_counter() - stage_started) * 1000, 2)
                    return response, metadata("semantic_hit", **{"X-Similarity": f"{similarity:.3f}"})
                except ValueError:
                    pass

            stage_started = time.perf_counter()
            article = self.cache.get_compiled_procedure(article_hash)
            stages["procedure_lookup"] = round((time.perf_counter() - stage_started) * 1000, 2)
            if article is not None and not self._article_matches_source(article, siis_payload, article_hash):
                article = None
            status = "procedure_hit" if article is not None else "miss"
            if article is None:
                stage_started = time.perf_counter()
                article = self.compiler.compile(siis_payload.title, siis_payload.content, article_hash)
                if self.hosted is not None:
                    hosted_calls += 1
                    article = self.hosted.structure(article, completion_deadline)
                stages["compilation"] = round((time.perf_counter() - stage_started) * 1000, 2)
            stage_started = time.perf_counter()
            response = self._render(article, complaint)
            stages["render_validation"] = round((time.perf_counter() - stage_started) * 1000, 2)
            if time.perf_counter() >= completion_deadline:
                raise TimeoutError("Application deadline exceeded")
            stage_started = time.perf_counter()
            try:
                if status == "miss":
                    self.cache.store_procedure(article)
                self.cache.store_answer(query, article_hash, complaint, response)
            except Exception:
                self.cache.discard_attempt(query, article_hash, new_procedure=status == "miss")
                raise
            if time.perf_counter() >= completion_deadline:
                self.cache.discard_attempt(query, article_hash, new_procedure=status == "miss")
                raise TimeoutError("Application deadline exceeded")
            stages["cache_store"] = round((time.perf_counter() - stage_started) * 1000, 2)
            return response, metadata(status)

    def preview(self, query: str, payload: SIISPayload, overrides: dict[str, bool | None] | None = None) -> dict[str, object]:
        complaint = self.normalizer.normalize(query)
        facts = dict(complaint.facts)
        evidence = dict(complaint.fact_evidence)
        for key, value in (overrides or {}).items():
            facts[key] = value
            evidence[key] = "preview override" if value is not None else "unknown by preview override"
        article = self.cache.get_compiled_procedure(self.article_hash(payload))
        if article is None:
            raise ValueError("Compiled article unavailable")
        selections: list[dict[str, object]] = []
        selected_catalog: dict[str, dict[str, str]] = {}
        selected_blocks: dict[str, dict[str, object]] = {}
        selected_operations: set[str] = set()
        for procedure in article.procedures:
            feature = procedure.feature_area
            off_topic = complaint.feature_area != "device" and feature in {"kids", "fingerprint", "keyboard", "email", "bluetooth", "multi window", "screen mirroring"} and feature != complaint.feature_area
            disposition = "excluded - off-topic" if off_topic else "included"
            actions: list[dict[str, object]] = []
            for action in procedure.actions:
                contradictions = [condition for condition in action.conditions if condition.fact in facts and facts[condition.fact] is not None and facts[condition.fact] != condition.expected]
                unknown = [condition for condition in action.conditions if facts.get(condition.fact) is None]
                applicability = "not applicable" if contradictions else ("needs confirmation" if unknown else "applicable")
                actions.append({
                    "id": action.id, "name": action.name, "operation": action.operation,
                    "source_ids": action.source_ids, "catalog_id": action.catalog_id,
                    "applicability": applicability,
                    "condition_reasons": [condition.text for condition in contradictions or unknown],
                })
                if not off_topic:
                    selected_operations.add(action.operation)
                    if action.catalog_id:
                        entry = self.resolver.by_id[action.catalog_id]
                        selected_catalog[action.catalog_id] = {"description": entry["description"], "deeplink": entry["deeplink"]}
                    for block in article.blocks:
                        if block.id in action.source_ids:
                            selected_blocks[block.id] = {"start": block.start, "end": block.end, "text": block.text}
            selections.append({"id": procedure.id, "title": procedure.title, "feature_area": feature, "disposition": disposition, "reason": "distinct feature without a dependency" if off_topic else "source procedure retained", "actions": actions})
        limitations: list[str] = []
        if not any(item["disposition"] == "included" for item in selections):
            limitations.append("No clearly relevant procedure in the supplied source")
        if complaint.requested_operation and complaint.requested_operation not in selected_operations:
            limitations.append("no source instruction for requested operation")
        return {
            "preview": {"procedures": selections, "facts": facts, "fact_provenance": evidence, "source_limitations": limitations},
            "evidence": {"article_hash": article.article_hash, "source_blocks": selected_blocks, "catalog": selected_catalog, "compilation_ledger": [entry.model_dump() for entry in article.ledger]},
        }
