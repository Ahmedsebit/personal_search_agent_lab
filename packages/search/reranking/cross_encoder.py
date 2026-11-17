from __future__ import annotations

from typing import Sequence

from packages.search.indexing.indexer import tokenize
from packages.search.models import Email, SearchResult


class TokenOverlapReranker:
    """Transparent M1 reranker, replaceable with a public cross-encoder later."""

    name = "token_overlap"

    def rerank(
        self, query: str, candidates: Sequence[SearchResult], documents: dict[str, Email], limit: int
    ) -> list[SearchResult]:
        query_tokens = set(tokenize(query))
        rescored: list[tuple[str, float]] = []
        for candidate in candidates:
            document = documents[candidate.document_id]
            document_tokens = set(tokenize(document.searchable_text))
            overlap = len(query_tokens & document_tokens) / max(len(query_tokens), 1)
            phrase_bonus = 1.0 if query.lower() in document.searchable_text.lower() else 0.0
            score = 0.25 * candidate.score + overlap + phrase_bonus
            rescored.append((candidate.document_id, score))
        rescored.sort(key=lambda item: (-item[1], item[0]))
        return [
            SearchResult(document_id=document_id, score=score, rank=rank, source=self.name)
            for rank, (document_id, score) in enumerate(rescored[:limit], start=1)
        ]
