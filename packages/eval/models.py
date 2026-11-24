from __future__ import annotations

from dataclasses import dataclass, field

from packages.search.query.context_aware_normalization import SuppressedAlias


@dataclass
class QueryEvaluation:
    query_id: str
    query: str
    scenario: str
    ranked_ids: list[str]
    metrics: dict[str, float]
    latency_ms: float


@dataclass
class ContextAwareQueryEvaluation(QueryEvaluation):
    source: str
    normalized_terms: tuple[str, ...]
    cohorts: tuple[str, ...]
    suppressed_aliases: tuple[SuppressedAlias, ...]


@dataclass
class ExperimentReport:
    name: str
    retriever: str
    query_count: int
    aggregate_metrics: dict[str, float]
    scenario_metrics: dict[str, dict[str, float]]
    latency: dict[str, float]
    per_query: list[QueryEvaluation] = field(default_factory=list)
