from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from packages.datasets.models import SearchQuery
from packages.eval.models import ExperimentReport, QueryEvaluation


def metrics_by_difficulty(report: ExperimentReport, queries: list[SearchQuery]) -> dict[str, dict[str, float]]:
    difficulty = {query.id: query.difficulty for query in queries}
    groups: dict[str, list[QueryEvaluation]] = defaultdict(list)
    for item in report.per_query:
        groups[difficulty.get(item.query_id, "unknown")].append(item)
    return {
        name: {
            metric: mean(item.metrics[metric] for item in items)
            for metric in items[0].metrics
        }
        for name, items in sorted(groups.items())
        if items
    }


def classify_failure(query: SearchQuery, evaluation: QueryEvaluation) -> list[str]:
    """Assign transparent benchmark-intent-based failure hypotheses."""
    if evaluation.metrics["ndcg@10"] >= 0.5:
        return []
    text = query.text.lower()
    intent = {str(key).lower(): str(value).lower() for key, value in query.intent.items()}
    notes = query.notes.lower()
    labels: list[str] = []

    if query.scenario == "recency" or any(word in text for word in ("latest", "recent", "newest", "last")):
        labels.append("temporal ordering not modeled")
    if any(marker in notes for marker in ("paraphrase", "semantic", "lexical gap")) or intent.get("variant") == "paraphrase":
        labels.append("semantic paraphrase gap")
    if any(marker in notes for marker in ("misspell", "typo")) or intent.get("variant") in {"misspelling", "typo"}:
        labels.append("misspelling not corrected")
    if any(marker in notes for marker in ("alias", "ambiguous")) or intent.get("variant") in {"alias", "ambiguous"}:
        labels.append("alias or ambiguous identity")
    if query.scenario in {"attachment", "thread"}:
        labels.append("structural field flattened into text")
    if query.scenario in {"topic", "person_topic", "mixed"} and evaluation.metrics["recall@50"] < 0.5:
        labels.append("broad intent or lexical candidate gap")
    if evaluation.metrics["recall@50"] >= 0.5 and evaluation.metrics["ndcg@10"] < 0.5:
        labels.append("hard-negative lexical competition or ordering failure")
    if not labels:
        labels.append("unclassified lexical ranking failure")
    return labels


def build_failure_taxonomy(report: ExperimentReport, queries: list[SearchQuery]) -> dict[str, dict[str, float | int]]:
    by_id = {query.id: query for query in queries}
    grouped: dict[str, list[QueryEvaluation]] = defaultdict(list)
    for item in report.per_query:
        query = by_id[item.query_id]
        for label in classify_failure(query, item):
            grouped[label].append(item)
    return {
        label: {
            "count": len(items),
            "mean_ndcg@10": mean(item.metrics["ndcg@10"] for item in items),
            "mean_recall@50": mean(item.metrics["recall@50"] for item in items),
        }
        for label, items in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    }


def analyze_report(report: ExperimentReport, queries: list[SearchQuery], worst_count: int = 20) -> dict[str, object]:
    by_id = {query.id: query for query in queries}
    worst = sorted(report.per_query, key=lambda item: (item.metrics["ndcg@10"], item.query_id))[:worst_count]
    return {
        "aggregate_metrics": report.aggregate_metrics,
        "scenario_metrics": report.scenario_metrics,
        "difficulty_metrics": metrics_by_difficulty(report, queries),
        "latency": report.latency,
        "worst_queries": [
            {
                "query_id": item.query_id,
                "query": item.query,
                "scenario": item.scenario,
                "difficulty": by_id[item.query_id].difficulty,
                "metrics": item.metrics,
                "failure_labels": classify_failure(by_id[item.query_id], item),
            }
            for item in worst
        ],
        "failure_taxonomy": build_failure_taxonomy(report, queries),
    }
