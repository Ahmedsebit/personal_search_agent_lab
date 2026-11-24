"""Adapt E002b's text mappings and term queries to the frozen E001 retriever."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from packages.search.models import Email
from packages.search.retrieval.bm25 import BM25Retriever as E001BM25Retriever
from packages.search.retrieval.simple_bm25 import SearchHit

__all__ = ["BM25Retriever"]


class BM25Retriever:
    def __init__(
        self,
        documents: Mapping[str, str],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self._bm25 = E001BM25Retriever(k1=k1, b=b)
        # Only the supplied text is searchable; placeholder fields add no tokens.
        self._bm25.index(
            [
                Email(
                    id=document_id,
                    owner_id="",
                    sender="",
                    recipients=(),
                    subject="",
                    body=text,
                    sent_at=datetime(1970, 1, 1, tzinfo=UTC),
                )
                for document_id, text in documents.items()
            ]
        )

    def search_terms(self, query_terms: Sequence[str], k: int = 50) -> list[SearchHit]:
        return self.search(" ".join(query_terms), k=k)

    def search(self, query: str, k: int = 50) -> list[SearchHit]:
        return [
            SearchHit(document_id=result.document_id, score=result.score)
            for result in self._bm25.search(query, k=k)
        ]
