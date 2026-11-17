from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from packages.search.interfaces import Retriever
from packages.search.models import Email, SearchResult


class ReciprocalRankFusionRetriever:
    name = "hybrid_rrf"

    def __init__(self, retrievers: Sequence[Retriever], rrf_k: int = 60, candidate_multiplier: int = 5) -> None:
        self.retrievers = list(retrievers)
        self.rrf_k = rrf_k
        self.candidate_multiplier = candidate_multiplier

    def index(self, documents: Sequence[Email]) -> None:
        for retriever in self.retrievers:
            retriever.index(documents)

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        scores: dict[str, float] = defaultdict(float)
        for retriever in self.retrievers:
            for result in retriever.search(query, limit * self.candidate_multiplier):
                scores[result.document_id] += 1.0 / (self.rrf_k + result.rank)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
        return [
            SearchResult(document_id=document_id, score=score, rank=rank, source=self.name)
            for rank, (document_id, score) in enumerate(ranked, start=1)
        ]
