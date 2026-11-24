from __future__ import annotations

import time
from collections import defaultdict

from packages.common.timing import percentile
from packages.datasets.models import RelevanceJudgment, SearchQuery
from packages.eval.metrics.ranking import evaluate_ranking
from packages.eval.models import ContextAwareQueryEvaluation, ExperimentReport, QueryEvaluation
from packages.search.interfaces import Reranker, Retriever
from packages.search.models import Email, SearchResult
from packages.search.retrieval.context_aware_bm25 import ContextAwareBM25Retriever


def run_experiment(
    name: str,
    retriever: Retriever | ContextAwareBM25Retriever,
    emails: list[Email],
    queries: list[SearchQuery],
    judgments: list[RelevanceJudgment],
    top_k: int = 50,
    reranker: Reranker | None = None,
    final_k: int = 10,
) -> ExperimentReport:
    if not isinstance(retriever, ContextAwareBM25Retriever):
        retriever.index(emails)
    documents = {document.id: document for document in emails}
    by_query: dict[str, dict[str, int]] = defaultdict(dict)
    for judgment in judgments:
        by_query[judgment.query_id][judgment.document_id] = judgment.relevance
    evaluations: list[QueryEvaluation] = []
    for query in queries:
        started = time.perf_counter()
        context_result = None
        if isinstance(retriever, ContextAwareBM25Retriever):
            context_result = retriever.search(query.text, top_k)
            results = [
                SearchResult(hit.document_id, hit.score, rank, context_result.source)
                for rank, hit in enumerate(context_result.hits, start=1)
            ]
        else:
            results = retriever.search(query.text, top_k)
        if reranker is not None:
            results = reranker.rerank(query.text, results, documents, final_k)
        elapsed_ms = (time.perf_counter() - started) * 1000
        ranked_ids = [result.document_id for result in results]
        grades = by_query.get(query.id, {})
        metrics = evaluate_ranking(ranked_ids, grades)
        evaluation: QueryEvaluation
        if context_result is not None:
            normalized = context_result.normalized_query
            evaluation = ContextAwareQueryEvaluation(
                query.id,
                query.text,
                query.scenario,
                ranked_ids,
                metrics,
                elapsed_ms,
                context_result.source,
                normalized.terms,
                normalized.cohorts,
                normalized.suppressed_aliases,
            )
        else:
            evaluation = QueryEvaluation(
                query.id, query.text, query.scenario, ranked_ids, metrics, elapsed_ms
            )
        evaluations.append(evaluation)
    metric_names = list(evaluations[0].metrics) if evaluations else []
    aggregate = {
        metric: sum(item.metrics[metric] for item in evaluations) / max(len(evaluations), 1)
        for metric in metric_names
    }
    scenarios: dict[str, list[QueryEvaluation]] = defaultdict(list)
    for item in evaluations:
        scenarios[item.scenario].append(item)
    scenario_metrics = {
        scenario: {
            metric: sum(item.metrics[metric] for item in items) / len(items)
            for metric in metric_names
        }
        for scenario, items in scenarios.items()
    }
    latencies = [item.latency_ms for item in evaluations]
    return ExperimentReport(
        name,
        reranker.name if reranker else retriever.name,
        len(queries),
        aggregate,
        scenario_metrics,
        {"p50_ms": percentile(latencies, 0.5), "p95_ms": percentile(latencies, 0.95)},
        evaluations,
    )
