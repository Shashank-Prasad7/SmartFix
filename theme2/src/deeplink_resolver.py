"""Deeplink Resolver for Samsung PRISM Hackathon (Theme 2).
Indexes 578 Galaxy Settings deeplinks using BM25 and all-MiniLM-L6-v2 embeddings.
Provides disambiguation (enable vs disable, Bluetooth vs Bluetooth scanning, Factory reset vs Auto reset)
and copies validation deeplinks verbatim from catalog.
"""
import json
import os
import re
from typing import Dict, List, Optional, Tuple

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from theme2.src.schema import (
    Condition,
    Deeplink,
    ResultTypes,
    ValidationDeepLink,
)


class DeeplinkResolver:
    _instance: Optional["DeeplinkResolver"] = None

    def __init__(self, catalog_path: Optional[str] = None):
        if catalog_path is None:
            # Default location
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            catalog_path = os.path.join(base_dir, "data", "student_kit", "deeplinks.json")

        self.catalog_path = catalog_path
        self.catalog: List[Dict] = []
        self.corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.embeddings: Optional[np.ndarray] = None
        self.model: Optional[SentenceTransformer] = None
        self._load_and_index()

    @classmethod
    def get_instance(cls, catalog_path: Optional[str] = None) -> "DeeplinkResolver":
        if cls._instance is None:
            cls._instance = cls(catalog_path)
        return cls._instance

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\b\w+\b", text.lower())

    def _load_and_index(self):
        if not os.path.exists(self.catalog_path):
            raise FileNotFoundError(f"Catalog file not found: {self.catalog_path}")

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.catalog = data.get("deeplinks", [])

        # Build corpus texts
        corpus_texts = []
        for item in self.catalog:
            desc = item.get("description", "")
            msg = item.get("message", "")
            qna = item.get("qna_description", "")
            orig_type = item.get("originalType", "")
            val_key = ""
            if item.get("validation") and isinstance(item["validation"], dict):
                val_key = item["validation"].get("key", "")
            
            full_text = f"{desc} {msg} {qna} {orig_type} {val_key}"
            corpus_texts.append(full_text)
            self.corpus.append(self._tokenize(full_text))

        # BM25 index
        self.bm25 = BM25Okapi(self.corpus)

        # Dense embedding index
        cache_embed_path = self.catalog_path.replace(".json", "_embeddings.npy")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
        if os.path.exists(cache_embed_path):
            self.embeddings = np.load(cache_embed_path)
        else:
            self.embeddings = self.model.encode(
                corpus_texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
            )
            np.save(cache_embed_path, self.embeddings)

    def resolve(
        self, query_or_step: str, operation_hint: Optional[str] = None
    ) -> Tuple[Optional[Deeplink], Optional[ValidationDeepLink], float]:
        """Resolves a step text or query to the best matching catalog Deeplink and ValidationDeepLink.
        Returns: (actionableDeeplink, validationDeeplink, confidence_score)
        """
        if not query_or_step or not self.catalog:
            return None, None, 0.0

        query_clean = query_or_step.lower()
        tokens = self._tokenize(query_clean)
        if not tokens:
            return None, None, 0.0

        # BM25 scores
        bm25_scores = np.array(self.bm25.get_scores(tokens))
        if bm25_scores.max() > 0:
            bm25_norm = bm25_scores / bm25_scores.max()
        else:
            bm25_norm = np.zeros(len(self.catalog))

        # Dense similarity
        query_embed = self.model.encode([query_or_step], normalize_embeddings=True, show_progress_bar=False)[0]
        dense_scores = np.dot(self.embeddings, query_embed)
        # Cosine similarity in [0, 1] range (clamped)
        dense_norm = np.clip((dense_scores + 1) / 2.0, 0.0, 1.0)

        # Combined hybrid score (0.4 BM25 + 0.6 Dense)
        combined_scores = 0.4 * bm25_norm + 0.6 * dense_norm

        # Apply domain disambiguation penalties/boosts:
        # 1. Bluetooth vs Bluetooth Scanning
        is_query_scanning = "scanning" in query_clean
        # 2. Factory data reset vs Auto factory reset
        is_query_auto_reset = "auto" in query_clean and "reset" in query_clean
        # 3. Enable vs Disable
        is_query_disable = any(w in query_clean for w in ["disable", "turn off", "turn-off", "deactivate", "off"])
        is_query_enable = any(w in query_clean for w in ["enable", "turn on", "turn-on", "activate", "on"])

        for i, item in enumerate(self.catalog):
            text_i = (item.get("description", "") + " " + item.get("message", "")).lower()
            orig_type = (item.get("originalType") or "").lower()

            # Disambiguate Bluetooth Scanning
            if "bluetooth" in text_i:
                item_is_scanning = "scanning" in text_i
                if is_query_scanning and not item_is_scanning:
                    combined_scores[i] *= 0.5
                elif not is_query_scanning and item_is_scanning:
                    combined_scores[i] *= 0.2  # Heavy penalty against unwanted scanning link

            # Disambiguate Auto Factory Reset vs Factory Reset
            if "reset" in text_i:
                item_is_auto = "auto" in text_i
                if is_query_auto_reset and not item_is_auto:
                    combined_scores[i] *= 0.5
                elif not is_query_auto_reset and item_is_auto:
                    combined_scores[i] *= 0.1  # Strong penalty for accidental auto reset

            # Disambiguate Enable vs Disable
            if is_query_disable:
                if orig_type == "offurl" or "turn off" in text_i or "disable" in text_i:
                    combined_scores[i] *= 1.3
                elif orig_type == "onurl":
                    combined_scores[i] *= 0.4
            elif is_query_enable:
                if orig_type == "onurl" or "turn on" in text_i or "enable" in text_i:
                    combined_scores[i] *= 1.3
                elif orig_type == "offurl":
                    combined_scores[i] *= 0.4

        best_idx = int(np.argmax(combined_scores))
        best_score = float(combined_scores[best_idx])

        # If confidence is too low (< 0.45) or no meaningful match
        if best_score < 0.45:
            # Fallback to dummy positive
            dummy_action = Deeplink(
                deeplink="bixby://dummy_positive",
                description="It will open the device settings screen",
                message="Open Settings",
                originalType="onClickURL"
            )
            return dummy_action, None, best_score

        best_item = self.catalog[best_idx]
        
        # Build Deeplink object
        actionable = Deeplink(
            deeplink=best_item.get("deeplink", "bixby://dummy_positive"),
            description=best_item.get("description", "It will configure the settings on device"),
            message=best_item.get("message", ""),
            originalType=best_item.get("originalType", None),
            classes=best_item.get("classes", None)
        )

        # Build ValidationDeepLink if present
        val_item = best_item.get("validation")
        validation = None
        if val_item and isinstance(val_item, dict) and val_item.get("deeplink"):
            # Map condition and resultType safely
            cond = None
            if val_item.get("condition") in [e.value for e in Condition]:
                cond = Condition(val_item["condition"])
            
            res_type = None
            if val_item.get("resultType") in [e.value for e in ResultTypes]:
                res_type = ResultTypes(val_item["resultType"])

            validation = ValidationDeepLink(
                deeplink=val_item.get("deeplink"),
                key=val_item.get("key", "Setting Status"),
                resultType=res_type,
                condition=cond,
                value=val_item.get("value", None)
            )

        return actionable, validation, best_score
