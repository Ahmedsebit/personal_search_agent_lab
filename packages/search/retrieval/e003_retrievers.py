"""E003 arms: E003-F, E003-T, E003-FT. The control (frozen E002b) is injected.

    control_search(query, top_k) -> [(doc_id, score), ...]   frozen E002b retriever
    normalize(query) -> str                                  frozen E002b normalizer
"""
from __future__ import annotations

from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from packages.search.query.field_cues import build_query_plan, default_tokenize, DEFAULT_FIELD_WEIGHTS
from packages.search.query.temporal_intent import detect_temporal_intent
from packages.search.retrieval.temporal_rerank import recency_rerank, FROZEN_LAMBDA

ARMS = ("control", "e003_f", "e003_t", "e003_ft")
Ranked = List[Tuple[str, float]]


class E003Retriever:
    def __init__(self, arm: str, *, control_search: Callable[[str, int], Ranked],
                 normalize: Callable[[str], str] = lambda q: q, field_index=None,
                 timestamps: Optional[Mapping] = None, tokenize=default_tokenize,
                 lam: float = FROZEN_LAMBDA, depth: int = 50, routing: bool = True,
                 field_weights: Optional[Dict[str, float]] = None):
        if arm not in ARMS:
            raise ValueError(f"unknown arm {arm!r}; expected one of {ARMS}")
        if arm in ("e003_f", "e003_ft") and field_index is None:
            raise ValueError(f"{arm} needs a FieldAwareBM25 index")
        if arm in ("e003_t", "e003_ft") and timestamps is None:
            raise ValueError(f"{arm} needs document timestamps")
        self.arm, self.control_search, self.normalize = arm, control_search, normalize
        self.field_index, self.timestamps, self.tokenize = field_index, timestamps, tokenize
        self.lam, self.depth, self.routing = lam, depth, routing
        self.field_weights = field_weights or DEFAULT_FIELD_WEIGHTS

    def _field_search(self, query: str, meta: dict) -> Ranked:
        plan = build_query_plan(self.normalize(query), self.tokenize, self.field_weights, self.routing)
        meta.update(plan.to_metadata())
        return self.field_index.search_plan(plan.terms, self.depth)

    def search(self, query: str, top_k: int = 50) -> Tuple[Ranked, dict]:
        meta: dict = {"arm": self.arm}
        if self.arm == "control":
            return list(self.control_search(query, top_k))[:top_k], meta
        if self.arm == "e003_f":
            return self._field_search(query, meta)[:top_k], meta

        intent = detect_temporal_intent(query)
        meta.update(intent.to_metadata())
        if not intent.fired:   # H4-T: non-temporal queries bypass the temporal layer entirely
            ranked = (list(self.control_search(query, top_k)) if self.arm == "e003_t"
                      else self._field_search(query, meta))
            return ranked[:top_k], meta
        cands = (list(self.control_search(intent.stripped_query, self.depth)) if self.arm == "e003_t"
                 else self._field_search(intent.stripped_query, meta))[: self.depth]
        meta["lambda"] = self.lam
        return recency_rerank(cands, self.timestamps, self.lam)[:top_k], meta
