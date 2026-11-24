from __future__ import annotations

from typing import Sequence

from packages.search.models import Email, SearchResult
from packages.search.query.normalization import NormalizedQuery, normalize_query
from packages.search.retrieval.bm25 import BM25Retriever


class QueryNormalizedBM25Retriever:
    """E002 retriever: explicit query normalization followed by frozen E001 BM25."""

    name = "query-normalized-bm25"

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._bm25 = BM25Retriever(k1=k1, b=b)
        self.last_normalization: NormalizedQuery | None = None

    def index(self, documents: Sequence[Email]) -> None:
        # E002 deliberately leaves corpus indexing identical to E001.
        self._bm25.index(documents)

    def search(self, query: str, k: int = 50, *, limit: int | None = None) -> list[SearchResult]:
        if limit is not None:
            k = limit
        normalized = normalize_query(query)
        self.last_normalization = normalized
        # BM25's tokenizer is unchanged. The normalizer supplies a space-separated
        # lexical query containing raw evidence plus only explicit E002 expansions.
        expanded_query = " ".join(normalized.terms)
        results = self._bm25.search(expanded_query, k=k)
        return [
            SearchResult(
                document_id=result.document_id,
                score=result.score,
                rank=result.rank,
                source=self.name,
            )
            for result in results
        ]
