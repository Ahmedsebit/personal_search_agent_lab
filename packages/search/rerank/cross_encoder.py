"""E008 re-rank scorers, CPU-only.

CrossEncoderScorer — preregistered model, loaded lazily (pip install sentence-transformers)
OverlapScorer      — deterministic token-overlap scorer; TESTS AND SMOKE RUNS ONLY
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from packages.search.retrieval.semantic_dense import document_text

PREREGISTERED_RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderScorer:
    def __init__(
        self,
        docs_by_id: Mapping[str, Mapping[str, str]],
        model: str = PREREGISTERED_RERANKER,
        max_length: int = 512,
        batch_size: int = 32,
    ) -> None:
        from sentence_transformers import CrossEncoder  # type: ignore[import-not-found]

        self.model = CrossEncoder(model, max_length=max_length, device="cpu")
        self.docs, self.batch_size, self.name = docs_by_id, batch_size, model

    def __call__(self, query: str, doc_ids: Sequence[str]) -> list[float]:
        pairs = [(query, document_text(self.docs[d])) for d in doc_ids]
        return [
            float(s)
            for s in self.model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
        ]


class OverlapScorer:
    name = "overlap-scorer (test only)"

    def __init__(self, docs_by_id: Mapping[str, Mapping[str, str]]) -> None:
        self.docs = docs_by_id

    def __call__(self, query: str, doc_ids: Sequence[str]) -> list[float]:
        q = set(re.findall(r"[a-z0-9]+", query.lower()))
        return [
            float(len(q & set(re.findall(r"[a-z0-9]+", document_text(self.docs[d]).lower()))))
            for d in doc_ids
        ]
