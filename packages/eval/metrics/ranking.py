from __future__ import annotations

import math
from collections.abc import Sequence


def _validate_k(k: int) -> None:
    if k <= 0:
        raise ValueError("k must be positive")


def precision_at_k(ranked_ids: Sequence[str], relevant: set[str], k: int) -> float:
    """Fraction of the first k ranks that are relevant."""
    _validate_k(k)
    return sum(document_id in relevant for document_id in ranked_ids[:k]) / k


def recall_at_k(ranked_ids: Sequence[str], relevant: set[str], k: int) -> float:
    """Fraction of all known relevant documents retrieved in the first k ranks."""
    _validate_k(k)
    if not relevant:
        return 0.0
    return sum(document_id in relevant for document_id in ranked_ids[:k]) / len(relevant)


def reciprocal_rank(ranked_ids: Sequence[str], relevant: set[str]) -> float:
    """Reciprocal rank of the first relevant result, or zero when none is retrieved."""
    for rank, document_id in enumerate(ranked_ids, start=1):
        if document_id in relevant:
            return 1.0 / rank
    return 0.0


def dcg_at_k(ranked_ids: Sequence[str], grades: dict[str, int], k: int) -> float:
    """Discounted cumulative gain using exponential graded relevance gain."""
    _validate_k(k)
    return sum(
        (2 ** grades.get(document_id, 0) - 1) / math.log2(rank + 1)
        for rank, document_id in enumerate(ranked_ids[:k], start=1)
    )


def ndcg_at_k(ranked_ids: Sequence[str], grades: dict[str, int], k: int) -> float:
    """DCG divided by the best DCG achievable from the available judgments."""
    _validate_k(k)
    actual = dcg_at_k(ranked_ids, grades, k)
    ideal_grades = sorted(grades.values(), reverse=True)[:k]
    ideal = sum(
        (2 ** grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(ideal_grades, start=1)
    )
    return actual / ideal if ideal else 0.0


def evaluate_ranking(
    ranked_ids: Sequence[str],
    grades: dict[str, int],
) -> dict[str, float]:
    """Return the standard E001 metrics for one ranked query result."""
    relevant = {document_id for document_id, grade in grades.items() if grade > 0}
    return {
        "precision@10": precision_at_k(ranked_ids, relevant, 10),
        "recall@10": recall_at_k(ranked_ids, relevant, 10),
        "recall@50": recall_at_k(ranked_ids, relevant, 50),
        "mrr": reciprocal_rank(ranked_ids, relevant),
        "dcg@10": dcg_at_k(ranked_ids, grades, 10),
        "ndcg@10": ndcg_at_k(ranked_ids, grades, 10),
    }
