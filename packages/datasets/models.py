from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchQuery:
    id: str
    text: str
    scenario: str


@dataclass(frozen=True)
class RelevanceJudgment:
    query_id: str
    document_id: str
    relevance: int
