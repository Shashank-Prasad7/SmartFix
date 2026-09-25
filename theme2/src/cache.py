"""Bounded, versioned answer and whole-article procedure caches."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from collections import OrderedDict
from pathlib import Path

from theme2.src.normalizer import NormalizedComplaint
from theme2.src.records import CompiledArticle
from theme2.src.schema import ContextDeeplinkResponse

PIPELINE_VERSION = "source-v2.24"
HOT_LIMIT = 512
DISK_LIMIT = 10_000


def compute_article_hash(title: str, content: str, catalog_digest: str = "", version: str = PIPELINE_VERSION) -> str:
    raw = json.dumps({"title": title, "content": content, "catalog": catalog_digest, "version": version}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_query_hash(query: str, article_hash: str) -> str:
    raw = json.dumps([query, article_hash], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


_SYNONYMS = {"flickers": "flicker", "flickering": "flicker", "dim": "dark", "darkness": "dark", "galaxy": "samsung", "phone": "device", "display": "screen", "broken": "damage", "damaged": "damage"}
_STOP = {
    "the", "a", "an", "is", "are", "my", "on", "and", "very", "has", "have", "it", "in", "to", "for", "with", "me", "when",
    "how", "can", "i", "resolve", "this", "issue", "please", "walk", "through", "fixing", "what", "troubleshooting", "steps", "apply",
    "need", "help", "following", "device", "problem", "which", "checks", "should", "perform", "symptom", "explain", "safe", "way", "address",
    "give", "guided", "situation", "diagnose", "handle", "first", "do", "if",
}


def _terms(query: str) -> set[str]:
    return {_SYNONYMS.get(term, term) for term in re.findall(r"[a-z0-9]+", query.lower()) if term not in _STOP}


class MultiTierCache:
    _instance: MultiTierCache | None = None
    _instance_lock = threading.Lock()

    def __init__(self, db_path: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        requested = db_path or os.getenv("PRISM_CACHE_DB_PATH")
        self.db_path = Path(requested).resolve() if requested else root / ".runtime" / "cache.sqlite3"
        if not self.db_path.is_relative_to(root):
            raise ValueError("Cache path must stay inside the project")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False, timeout=5)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("CREATE TABLE IF NOT EXISTS procedures (article_hash TEXT PRIMARY KEY, body TEXT NOT NULL, touched INTEGER NOT NULL DEFAULT 0)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS answers (query_hash TEXT PRIMARY KEY, article_hash TEXT NOT NULL, query TEXT NOT NULL, compatibility TEXT NOT NULL, body TEXT NOT NULL, touched INTEGER NOT NULL DEFAULT 0)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS answers_article ON answers(article_hash)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS procedures_touched ON procedures(touched)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS answers_touched ON answers(touched)")
        self.connection.commit()
        self.hot_answers: OrderedDict[str, ContextDeeplinkResponse] = OrderedDict()
        self.hot_procedures: OrderedDict[str, CompiledArticle] = OrderedDict()

    @classmethod
    def get_instance(cls) -> MultiTierCache:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def close(self) -> None:
        """Release a cache connection for clean shutdown or restart checks."""
        with self.lock:
            self.connection.close()

    @staticmethod
    def _remember(cache: OrderedDict, key: str, value: object) -> None:
        cache[key] = value
        cache.move_to_end(key)
        if len(cache) > HOT_LIMIT:
            cache.popitem(last=False)

    def get_exact_answer(self, query: str, article_hash: str) -> ContextDeeplinkResponse | None:
        key = compute_query_hash(query, article_hash)
        with self.lock:
            value = self.hot_answers.get(key)
            if value is None:
                row = self.connection.execute("SELECT body FROM answers WHERE query_hash=?", (key,)).fetchone()
                if row:
                    try:
                        value = ContextDeeplinkResponse.model_validate_json(row[0])
                        self._remember(self.hot_answers, key, value)
                    except ValueError:
                        return None
            return value.model_copy(deep=True) if value else None

    def get_semantic_answer(self, query: str, article_hash: str, normalized: NormalizedComplaint, threshold: float = 0.62) -> tuple[ContextDeeplinkResponse, float, str] | None:
        compatibility = json.dumps(normalized.compatibility_key(), ensure_ascii=False)
        query_terms = _terms(query)
        if not query_terms:
            return None
        with self.lock:
            rows = self.connection.execute("SELECT query, body FROM answers WHERE article_hash=? AND compatibility=? ORDER BY touched DESC LIMIT 100", (article_hash, compatibility)).fetchall()
        best: tuple[str, str, float] | None = None
        for cached_query, body in rows:
            candidate_terms = _terms(cached_query)
            similarity = len(query_terms & candidate_terms) / max(1, len(query_terms | candidate_terms))
            if similarity >= threshold and (best is None or similarity > best[2]):
                best = cached_query, body, similarity
        if best:
            try:
                return ContextDeeplinkResponse.model_validate_json(best[1]), best[2], best[0]
            except ValueError:
                return None
        return None

    def get_compiled_procedure(self, article_hash: str) -> CompiledArticle | None:
        with self.lock:
            value = self.hot_procedures.get(article_hash)
            if value is None:
                row = self.connection.execute("SELECT body FROM procedures WHERE article_hash=?", (article_hash,)).fetchone()
                if row:
                    try:
                        value = CompiledArticle.model_validate_json(row[0])
                        value.validate_structure()
                        self._remember(self.hot_procedures, article_hash, value)
                    except ValueError:
                        return None
            return value.model_copy(deep=True) if value else None

    def store_procedure(self, article: CompiledArticle) -> None:
        article.validate_structure()
        with self.lock:
            self.connection.execute("INSERT OR REPLACE INTO procedures(article_hash, body, touched) VALUES (?, ?, ?)", (article.article_hash, article.model_dump_json(), time.time_ns()))
            excess = self.connection.execute("SELECT COUNT(*) FROM procedures").fetchone()[0] - DISK_LIMIT
            if excess > 0:
                evicted = [row[0] for row in self.connection.execute("SELECT article_hash FROM procedures ORDER BY touched ASC, rowid ASC LIMIT ?", (excess,))]
                self.connection.executemany("DELETE FROM procedures WHERE article_hash=?", ((key,) for key in evicted))
                for key in evicted:
                    self.hot_procedures.pop(key, None)
            self.connection.commit()
            self._remember(self.hot_procedures, article.article_hash, article.model_copy(deep=True))

    def store_answer(self, query: str, article_hash: str, normalized: NormalizedComplaint, response: ContextDeeplinkResponse) -> None:
        key = compute_query_hash(query, article_hash)
        compatibility = json.dumps(normalized.compatibility_key(), ensure_ascii=False)
        with self.lock:
            self.connection.execute("INSERT OR REPLACE INTO answers(query_hash, article_hash, query, compatibility, body, touched) VALUES (?, ?, ?, ?, ?, ?)", (key, article_hash, query, compatibility, response.model_dump_json(), time.time_ns()))
            excess = self.connection.execute("SELECT COUNT(*) FROM answers").fetchone()[0] - DISK_LIMIT
            if excess > 0:
                evicted = [row[0] for row in self.connection.execute("SELECT query_hash FROM answers ORDER BY touched ASC, rowid ASC LIMIT ?", (excess,))]
                self.connection.executemany("DELETE FROM answers WHERE query_hash=?", ((item,) for item in evicted))
                for item in evicted:
                    self.hot_answers.pop(item, None)
            self.connection.commit()
            self._remember(self.hot_answers, key, response.model_copy(deep=True))

    def discard_attempt(self, query: str, article_hash: str, *, new_procedure: bool) -> None:
        """Remove artifacts from a request that failed its completion budget."""
        key = compute_query_hash(query, article_hash)
        with self.lock:
            self.connection.execute("DELETE FROM answers WHERE query_hash=?", (key,))
            self.hot_answers.pop(key, None)
            if new_procedure:
                self.connection.execute("DELETE FROM procedures WHERE article_hash=?", (article_hash,))
                self.hot_procedures.pop(article_hash, None)
            self.connection.commit()
