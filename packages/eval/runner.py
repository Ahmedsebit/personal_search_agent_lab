from __future__ import annotations

import time
from collections import defaultdict

from packages.common.timing import percentile
from packages.datasets.models import RelevanceJudgment, SearchQuery
from packages.eval.metrics.ranking import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
from packages.eval.models import ExperimentReport, QueryEvaluation
from packages.search.interfaces import Reranker, Retriever
from packages.search.models import Email


def run_experiment(name: str, retriever: Retriever, emails: list[Email], queries: list[SearchQuery], judgments: list[RelevanceJudgment], top_k: int = 50, reranker: Reranker | None = None, final_k: int = 10) -> ExperimentReport:
    retriever.index(emails)
    documents = {document.id: document for document in emails}
    by_query: dict[str, dict[str, int]] = defaultdict(dict)
    for judgment in judgments: by_query[judgment.query_id][judgment.document_id] = judgment.relevance
    evaluations: list[QueryEvaluation] = []
    for query in queries:
        started = time.perf_counter()
        results = retriever.search(query.text, top_k)
        if reranker is not None: results = reranker.rerank(query.text, results, documents, final_k)
        elapsed_ms = (time.perf_counter() - started) * 1000
        ranked_ids = [result.document_id for result in results]
        grades = by_query.get(query.id, {})
        relevant = {document_id for document_id, grade in grades.items() if grade > 0}
        metrics = {
            "precision@10": precision_at_k(ranked_ids, relevant, 10),
            "recall@10": recall_at_k(ranked_ids, relevant, 10),
            "recall@50": recall_at_k(ranked_ids, relevant, 50),
            "mrr": reciprocal_rank(ranked_ids, relevant),
            "ndcg@10": ndcg_at_k(ranked_ids, grades, 10),
        }
        evaluations.append(QueryEvaluation(query.id, query.text, query.scenario, ranked_ids, metrics, elapsed_ms))
    metric_names = list(evaluations[0].metrics) if evaluations else []
    aggregate = {metric: sum(item.metrics[metric] for item in evaluations) / max(len(evaluations), 1) for metric in metric_names}
    scenarios: dict[str, list[QueryEvaluation]] = defaultdict(list)
    for item in evaluations: scenarios[item.scenario].append(item)
    scenario_metrics = {scenario: {metric: sum(item.metrics[metric] for item in items) / len(items) for metric in metric_names} for scenario, items in scenarios.items()}
    latencies = [item.latency_ms for item in evaluations]
    return ExperimentReport(name, reranker.name if reranker else retriever.name, len(queries), aggregate, scenario_metrics, {"p50_ms": percentile(latencies, .5), "p95_ms": percentile(latencies, .95)}, evaluations)
