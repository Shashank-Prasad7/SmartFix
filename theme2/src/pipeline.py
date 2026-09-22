"""Troubleshooting Pipeline for Samsung PRISM Hackathon Theme 2.
Coordinates:
- Input validation
- Tier 1 exact cache (<10ms)
- Tier 2 semantic paraphrase cache (<50ms)
- Tier 3 compiled procedure cache
- Stage 1 complaint normalization
- Stage 2 SIIS procedure compilation & deeplink resolution
- Sanitization & scoring gate enforcement
"""
import time
from typing import Dict, Optional, Tuple

from theme2.src.cache import (
    MultiTierCache,
    compute_article_hash,
)
from theme2.src.compiler import SIISCompiler
from theme2.src.deeplink_resolver import DeeplinkResolver
from theme2.src.normalizer import ComplaintNormalizer
from theme2.src.sanitizer import sanitize_response
from theme2.src.schema import (
    ContextDeeplinkResponse,
    SIISPayload,
)


class TroubleshootingPipeline:
    _instance: Optional["TroubleshootingPipeline"] = None

    def __init__(self):
        self.resolver = DeeplinkResolver.get_instance()
        self.normalizer = ComplaintNormalizer.get_instance()
        self.compiler = SIISCompiler.get_instance()
        self.cache = MultiTierCache.get_instance()

    @classmethod
    def get_instance(cls) -> "TroubleshootingPipeline":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def process(
        self, query: str, siis_payload: SIISPayload
    ) -> Tuple[ContextDeeplinkResponse, Dict[str, str]]:
        """Processes a query and SIIS response.
        Returns: (ContextDeeplinkResponse, metadata_headers)
        """
        start_time = time.perf_counter()
        art_hash = compute_article_hash(siis_payload.title, siis_payload.content)

        # 1. Tier 1: Exact Answer Cache
        cached_exact = self.cache.get_exact_answer(query, art_hash)
        if cached_exact:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            headers = {
                "X-Cache-Status": "exact_hit",
                "X-Processing-Time-Ms": f"{elapsed_ms:.2f}",
            }
            return cached_exact, headers

        # 2. Compute query embedding for semantic lookup & caching
        query_embed = self.resolver.model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]

        # 3. Tier 2: Semantic Paraphrase Cache
        cached_semantic = self.cache.get_semantic_answer(query, art_hash, query_embed, similarity_threshold=0.85)
        if cached_semantic:
            resp, sim, matched_q = cached_semantic
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            headers = {
                "X-Cache-Status": "semantic_hit",
                "X-Matched-Query": matched_q,
                "X-Similarity": f"{sim:.3f}",
                "X-Processing-Time-Ms": f"{elapsed_ms:.2f}",
            }
            # Record this new query in exact answer cache as well for future instant lookup
            self.cache.store_answer(query, art_hash, resp, query_embed)
            return resp, headers

        # 4. Tier 3: Compiled Procedure Cache
        cached_proc = self.cache.get_compiled_procedure(art_hash)
        if cached_proc:
            # We already have the compiled procedure for this article
            # Re-normalize complaint for accurate goal/title relevance
            normalized = self.normalizer.normalize(query)
            # Clone procedure and update goal score
            resp_copy = ContextDeeplinkResponse.model_validate(cached_proc.model_dump())
            if resp_copy.contexts:
                resp_copy.contexts[0].goal = f"Follow these steps to perform this {normalized.feature_area} {normalized.intent}."
                resp_copy.contexts[0].title = f"{normalized.feature_area} Fix"
            sanitized = sanitize_response(resp_copy)

            self.cache.store_answer(query, art_hash, sanitized, query_embed)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            headers = {
                "X-Cache-Status": "procedure_hit",
                "X-Processing-Time-Ms": f"{elapsed_ms:.2f}",
            }
            return sanitized, headers

        # 5. Cold Execution
        normalized = self.normalizer.normalize(query)
        compiled_resp = self.compiler.compile(normalized, siis_payload.title, siis_payload.content)
        sanitized_resp = sanitize_response(compiled_resp)

        # Store in caches
        self.cache.store_procedure(art_hash, siis_payload.title, sanitized_resp)
        self.cache.store_answer(query, art_hash, sanitized_resp, query_embed)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        headers = {
            "X-Cache-Status": "miss",
            "X-Processing-Time-Ms": f"{elapsed_ms:.2f}",
        }
        return sanitized_resp, headers
