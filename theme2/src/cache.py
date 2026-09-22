"""Multi-tier Cache for Samsung PRISM Hackathon Theme 2.
Implements:
1. In-memory LRU cache (< 5ms response)
2. SQLite persistent cache
3. Semantic Paraphrase cache (< 50ms response, >= 80% hit target)
4. Procedure cache for pre-compiled SIIS articles
"""
import hashlib
import json
import os
import sqlite3
from typing import Dict, List, Optional, Tuple

import numpy as np

from theme2.src.schema import ContextDeeplinkResponse


def compute_article_hash(title: str, content: str) -> str:
    text = f"{title.strip()}\n{content.strip()}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_query_hash(query: str, article_hash: str) -> str:
    combined = f"{query.strip().lower()}:{article_hash}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


class MultiTierCache:
    _instance: Optional["MultiTierCache"] = None

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "cache.db")

        self.db_path = db_path
        self.memory_answer_cache: Dict[str, ContextDeeplinkResponse] = {}
        self.memory_procedure_cache: Dict[str, ContextDeeplinkResponse] = {}
        # Article hash -> List of (query_text, query_embed, response_obj)
        self.semantic_index: Dict[str, List[Tuple[str, np.ndarray, ContextDeeplinkResponse]]] = {}
        self._init_sqlite()
        self._load_warm_cache()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> "MultiTierCache":
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    def _init_sqlite(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # Answer cache table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS answers (
                query_hash TEXT PRIMARY KEY,
                query_text TEXT,
                article_hash TEXT,
                response_json TEXT,
                embedding_blob BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Procedure cache table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS procedures (
                article_hash TEXT PRIMARY KEY,
                title TEXT,
                procedure_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def _load_warm_cache(self):
        """Loads cached answers and procedures into memory for instantaneous lookup."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # Load procedures
        cur.execute("SELECT article_hash, procedure_json FROM procedures")
        for art_hash, proc_json in cur.fetchall():
            try:
                resp = ContextDeeplinkResponse.model_validate_json(proc_json)
                self.memory_procedure_cache[art_hash] = resp
            except Exception:
                pass

        # Load answers
        cur.execute("SELECT query_hash, query_text, article_hash, response_json, embedding_blob FROM answers")
        for q_hash, q_text, art_hash, resp_json, emb_blob in cur.fetchall():
            try:
                resp = ContextDeeplinkResponse.model_validate_json(resp_json)
                self.memory_answer_cache[q_hash] = resp
                if emb_blob:
                    emb = np.frombuffer(emb_blob, dtype=np.float32)
                    if art_hash not in self.semantic_index:
                        self.semantic_index[art_hash] = []
                    self.semantic_index[art_hash].append((q_text, emb, resp))
            except Exception:
                pass

        conn.close()

    def get_exact_answer(self, query: str, article_hash: str) -> Optional[ContextDeeplinkResponse]:
        """Tier 1: Checks in-memory exact hash lookup."""
        q_hash = compute_query_hash(query, article_hash)
        return self.memory_answer_cache.get(q_hash)

    def get_semantic_answer(
        self, query: str, article_hash: str, query_embed: np.ndarray, similarity_threshold: float = 0.85
    ) -> Optional[Tuple[ContextDeeplinkResponse, float, str]]:
        """Tier 2: Checks semantic paraphrase similarity across cached queries for this article."""
        candidates = self.semantic_index.get(article_hash)
        if not candidates:
            return None

        best_sim = -1.0
        best_resp = None
        best_matched_q = ""

        # Normalize query embedding
        norm = np.linalg.norm(query_embed)
        if norm > 0:
            q_norm = query_embed / norm
        else:
            q_norm = query_embed

        for cached_q, cached_emb, cached_resp in candidates:
            c_norm_val = np.linalg.norm(cached_emb)
            c_norm = cached_emb / c_norm_val if c_norm_val > 0 else cached_emb
            sim = float(np.dot(q_norm, c_norm))
            if sim > best_sim:
                best_sim = sim
                best_resp = cached_resp
                best_matched_q = cached_q

        if best_sim >= similarity_threshold and best_resp is not None:
            return best_resp, best_sim, best_matched_q

        return None

    def get_compiled_procedure(self, article_hash: str) -> Optional[ContextDeeplinkResponse]:
        """Tier 3: Checks if this SIIS article has already been compiled."""
        return self.memory_procedure_cache.get(article_hash)

    def store_answer(
        self,
        query: str,
        article_hash: str,
        response: ContextDeeplinkResponse,
        query_embed: Optional[np.ndarray] = None,
    ):
        q_hash = compute_query_hash(query, article_hash)
        self.memory_answer_cache[q_hash] = response
        resp_json = response.model_dump_json()

        emb_blob = query_embed.astype(np.float32).tobytes() if query_embed is not None else None

        if query_embed is not None:
            if article_hash not in self.semantic_index:
                self.semantic_index[article_hash] = []
            self.semantic_index[article_hash].append((query, query_embed, response))

        # Write to SQLite
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO answers (query_hash, query_text, article_hash, response_json, embedding_blob)
            VALUES (?, ?, ?, ?, ?)
        """,
            (q_hash, query, article_hash, resp_json, emb_blob),
        )
        conn.commit()
        conn.close()

    def store_procedure(self, article_hash: str, title: str, response: ContextDeeplinkResponse):
        self.memory_procedure_cache[article_hash] = response
        resp_json = response.model_dump_json()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO procedures (article_hash, title, procedure_json)
            VALUES (?, ?, ?)
        """,
            (article_hash, title, resp_json),
        )
        conn.commit()
        conn.close()
