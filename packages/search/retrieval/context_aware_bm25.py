"""Separate E002b retriever wrapping frozen BM25 scoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from packages.search.query.context_aware_normalization import (
    ContextAwareQueryNormalizer,
    NormalizedQuery,
)
from packages.search.retrieval.e001_adapter import BM25Retriever
from packages.search.retrieval.simple_bm25 import SearchHit


class _TermRetriever(Protocol):
    def search_terms(self, query_terms: Sequence[str], k: int = 50) -> list[SearchHit]: ...


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    normalized_query: NormalizedQuery
    hits: tuple[SearchHit, ...]
    source: str = "context-aware-query-normalized-bm25"


class ContextAwareBM25Retriever:
    """E002b query understanding plus unchanged BM25 candidate retrieval."""

    name = "context-aware-query-normalized-bm25"

    def __init__(
        self,
        documents: Mapping[str, str],
        *,
        normalizer: ContextAwareQueryNormalizer,
        bm25: _TermRetriever | None = None,
    ) -> None:
        self.normalizer = normalizer
        self.bm25 = bm25 if bm25 is not None else BM25Retriever(documents)

    def search(self, query: str, k: int = 50) -> RetrievalResult:
        normalized = self.normalizer.normalize(query)
        hits = self.bm25.search_terms(normalized.terms, k=k)
        return RetrievalResult(
            query=query,
            normalized_query=normalized,
            hits=tuple(hits),
        )
