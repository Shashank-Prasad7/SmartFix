"""Read-only catalog lookup with explicit setting and operation guards.

An optional, already downloaded MiniLM model can be enabled with
``PRISM_MINILM_PATH``. Startup never downloads a model.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from threading import Lock
from typing import Any

from rank_bm25 import BM25Okapi

from theme2.src.schema import (
    Condition,
    ContextDeeplinkResponse,
    Deeplink,
    ResultTypes,
    ValidationDeepLink,
)


def tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


class DeeplinkResolver:
    """Catalog materializer. Generic button labels never establish identity."""

    _instance: DeeplinkResolver | None = None
    _instance_lock = Lock()

    def __init__(self, catalog_path: str | Path | None = None) -> None:
        self.catalog_path = Path(catalog_path) if catalog_path else Path(__file__).resolve().parents[1] / "data" / "official" / "student_kit" / "deeplinks.json"
        raw = self.catalog_path.read_bytes()
        self.catalog_digest = hashlib.sha256(raw).hexdigest()
        self.catalog: list[dict[str, Any]] = json.loads(raw)["deeplinks"]
        self.by_id = {entry["id"]: entry for entry in self.catalog}
        self.by_uri: dict[str, list[str]] = {}
        for entry in self.catalog:
            self.by_uri.setdefault(entry["deeplink"], []).append(entry["id"])
        self.identities = [self._identity(entry) for entry in self.catalog]
        self.corpus = [tokens(f"{identity} {entry.get('description', '')} {entry.get('qna_description', '')}") for identity, entry in zip(self.identities, self.catalog)]
        self.bm25 = BM25Okapi(self.corpus)
        self.model = None
        self.embeddings = None
        model_path = os.getenv("PRISM_MINILM_PATH")
        if model_path and Path(model_path).is_dir():
            try:
                import numpy as np
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(model_path, local_files_only=True)
                descriptions = [f"{identity} {entry.get('description', '')}" for identity, entry in zip(self.identities, self.catalog)]
                self.embeddings = np.asarray(self.model.encode(descriptions, normalize_embeddings=True, show_progress_bar=False))
            except (ImportError, OSError, ValueError):
                self.model = None
                self.embeddings = None
        self.index_version = f"minilm:{Path(model_path).resolve()}:{os.getenv('PRISM_MINILM_VERSION', 'local')}" if self.model is not None and model_path else "bm25"

    @classmethod
    def get_instance(cls) -> DeeplinkResolver:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    @staticmethod
    def _identity(entry: dict[str, Any]) -> str:
        validation = entry.get("validation") or {}
        if validation.get("key"):
            return str(validation["key"]).lower()
        description = str(entry.get("description", ""))
        match = re.search(r"(?:opens the|enables|disables) (.*?) (?:settings|via device Settings|page in device Settings)", description, re.IGNORECASE)
        return (match.group(1) if match else description).strip().lower()

    @staticmethod
    def _operation(entry: dict[str, Any]) -> str:
        kind = entry.get("originalType")
        if kind == "onURL":
            return "enable"
        if kind == "offURL":
            return "disable"
        return "open"

    def resolve(self, text: str, operation_hint: str | None = None, setting_hint: str | None = None) -> tuple[Deeplink | None, ValidationDeepLink | None, float, str | None]:
        """Return catalog metadata only when identity and operation agree."""
        if not text.strip():
            return None, None, 0.0, None
        operation = operation_hint or "open"
        if operation not in {"open", "enable", "disable", "update"}:
            return None, None, 0.0, None
        query_terms = set(tokens(setting_hint or text)) - {"settings", "setting", "device", "phone", "open", "tap", "turn", "on", "off", "the", "to", "and"}
        if not query_terms:
            return None, None, 0.0, None
        scores = self.bm25.get_scores(list(query_terms))
        ranking = scores
        if self.model is not None and self.embeddings is not None:
            try:
                import numpy as np

                vector = np.asarray(self.model.encode([setting_hint or text], normalize_embeddings=True, show_progress_bar=False))[0]
                lexical = scores / max(1.0, float(scores.max()))
                dense = np.clip(self.embeddings @ vector, 0.0, 1.0)
                ranking = 0.55 * lexical + 0.45 * dense
            except (OSError, RuntimeError, ValueError):
                ranking = scores
        ranked = sorted(range(len(ranking)), key=lambda index: float(ranking[index]), reverse=True)
        best: tuple[int, float] | None = None
        for index in ranked[:35]:
            entry = self.catalog[index]
            if self._operation(entry) != operation:
                continue
            identity_terms = set(tokens(self.identities[index]))
            # A partial lexical match is unsafe for an actionable link: "safe
            # mode" used to resolve to TV picture mode, and "multi window"
            # to Multi Control. BM25 only proposes candidates; identity is a
            # hard gate. Qualifiers such as scanning, auto, menu and vibration
            # are part of the setting, not expendable search terms.
            if identity_terms != query_terms:
                continue
            if "bluetooth" in query_terms and ("scanning" in identity_terms) != ("scanning" in query_terms):
                continue
            if "scanning" in identity_terms and "scanning" not in query_terms:
                continue
            if "factory" in query_terms and "reset" in query_terms and ("auto" in identity_terms) != ("auto" in query_terms):
                continue
            if "music" in identity_terms and "music" not in query_terms:
                continue
            confidence = 1.0
            if best is None or confidence > best[1]:
                best = index, confidence
        if best is None:
            return None, None, 0.0, None
        entry = self.catalog[best[0]]
        action, validation = self.materialize(entry["id"])
        return action, validation, best[1], entry["id"]

    def materialize(self, catalog_id: str) -> tuple[Deeplink, ValidationDeepLink | None]:
        """Copy link and validation from one immutable catalog entry."""
        entry = self.by_id[catalog_id]
        action = Deeplink(deeplink=entry["deeplink"], description=entry["description"], message=entry.get("message"), classes=entry.get("classes"), originalType=entry.get("originalType"))
        validation_data = entry.get("validation") or {}
        validation = None
        if validation_data.get("deeplink") and validation_data.get("key"):
            validation = ValidationDeepLink(
                deeplink=validation_data["deeplink"], key=validation_data["key"],
                resultType=ResultTypes(validation_data["resultType"]) if validation_data.get("resultType") in ResultTypes._value2member_map_ else None,
                condition=Condition(validation_data["condition"]) if validation_data.get("condition") in Condition._value2member_map_ else None,
                value=validation_data.get("value"),
            )
        return action, validation

    def validate_response_links(self, response: ContextDeeplinkResponse) -> None:
        """Check complete action/validation pairs against one catalog row."""
        for goal in response.contexts:
            for action in goal.actions:
                for group in action.stepGroups:
                    link, validation = group.actionableDeeplink, group.validationDeeplink
                    if link is None:
                        if validation is not None:
                            raise ValueError("Validation without an actionable catalog link")
                        continue
                    if link.deeplink == "bixby://dummy_positive":
                        if validation is not None or link.originalType != "onClickURL":
                            raise ValueError("Invalid dummy link metadata")
                        continue
                    candidates = self.by_uri.get(link.deeplink, [])
                    if not any(
                        link == expected_link and validation == expected_validation
                        for catalog_id in candidates
                        for expected_link, expected_validation in [self.materialize(catalog_id)]
                    ):
                        raise ValueError("Action or validation metadata differs from the approved catalog")
