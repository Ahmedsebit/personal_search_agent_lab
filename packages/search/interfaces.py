from __future__ import annotations

from typing import Protocol, Sequence

from packages.search.models import Email, SearchResult


class Retriever(Protocol):
    name: str

    def index(self, documents: Sequence[Email]) -> None: ...

    def search(self, query: str, limit: int = 10) -> list[SearchResult]: ...


class Reranker(Protocol):
    name: str

    def rerank(
        self, query: str, candidates: Sequence[SearchResult], documents: dict[str, Email], limit: int
    ) -> list[SearchResult]: ...
