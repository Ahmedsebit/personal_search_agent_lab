from __future__ import annotations

import math
from collections.abc import Sequence


def precision_at_k(ranked_ids: Sequence[str], relevant: set[str], k: int) -> float:
    if k <= 0: raise ValueError("k must be positive")
    return sum(document_id in relevant for document_id in ranked_ids[:k]) / k


def recall_at_k(ranked_ids: Sequence[str], relevant: set[str], k: int) -> float:
    if k <= 0: raise ValueError("k must be positive")
    if not relevant: return 0.0
    return sum(document_id in relevant for document_id in ranked_ids[:k]) / len(relevant)


def reciprocal_rank(ranked_ids: Sequence[str], relevant: set[str]) -> float:
    for rank, document_id in enumerate(ranked_ids, start=1):
        if document_id in relevant: return 1.0 / rank
    return 0.0


def dcg_at_k(ranked_ids: Sequence[str], grades: dict[str, int], k: int) -> float:
    if k <= 0: raise ValueError("k must be positive")
    return sum((2 ** grades.get(document_id, 0) - 1) / math.log2(rank + 1) for rank, document_id in enumerate(ranked_ids[:k], start=1))


def ndcg_at_k(ranked_ids: Sequence[str], grades: dict[str, int], k: int) -> float:
    actual = dcg_at_k(ranked_ids, grades, k)
    ideal_grades = sorted(grades.values(), reverse=True)[:k]
    ideal = sum((2 ** grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal_grades, start=1))
    return actual / ideal if ideal else 0.0
