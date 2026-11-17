import pytest
from packages.eval.metrics.ranking import dcg_at_k, ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank


def test_perfect_ranking():
    ranked = ["a", "b", "c"]
    relevant = {"a", "b"}
    grades = {"a": 3, "b": 2}
    assert precision_at_k(ranked, relevant, 2) == 1.0
    assert recall_at_k(ranked, relevant, 2) == 1.0
    assert reciprocal_rank(ranked, relevant) == 1.0
    assert ndcg_at_k(ranked, grades, 2) == pytest.approx(1.0)
    assert dcg_at_k(ranked, grades, 2) > 0


def test_empty_relevance():
    assert recall_at_k(["a"], set(), 10) == 0.0
    assert reciprocal_rank(["a"], set()) == 0.0
    assert ndcg_at_k(["a"], {}, 10) == 0.0


def test_invalid_k():
    with pytest.raises(ValueError): precision_at_k([], set(), 0)
