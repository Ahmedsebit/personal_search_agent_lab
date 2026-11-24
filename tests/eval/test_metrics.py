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

from packages.eval.metrics.ranking import evaluate_ranking


def test_recall_toy_example():
    relevant = {f"r{i}" for i in range(1, 9)}
    ranked = ["r1", "x1", "r2", "x2", "r3", "x3", "x4", "x5", "x6", "x7"]
    assert recall_at_k(ranked, relevant, 10) == pytest.approx(3 / 8)


def test_recall_at_50_can_reveal_deeper_retrieval_headroom():
    relevant = {f"r{i}" for i in range(1, 9)}
    ranked = ["r1", "x1", "r2", "x2", "r3"] + [f"x{i}" for i in range(3, 38)] + ["r4", "r5", "r6", "r7", "r8"]
    assert recall_at_k(ranked, relevant, 10) == pytest.approx(3 / 8)
    assert recall_at_k(ranked, relevant, 50) == pytest.approx(1.0)


def test_reciprocal_rank_rewards_earlier_first_relevant_result():
    relevant = {"r"}
    assert reciprocal_rank(["r", "x"], relevant) > reciprocal_rank(["x", "r"], relevant)


def test_ndcg_rewards_better_graded_order():
    grades = {"best": 3, "good": 2, "ok": 1}
    ideal = ["best", "good", "ok"]
    reversed_order = ["ok", "good", "best"]
    assert ndcg_at_k(ideal, grades, 3) == pytest.approx(1.0)
    assert ndcg_at_k(ideal, grades, 3) > ndcg_at_k(reversed_order, grades, 3)


def test_evaluate_ranking_returns_e001_metric_set():
    metrics = evaluate_ranking(["a", "b", "c"], {"a": 3, "c": 1})
    assert set(metrics) == {"precision@10", "recall@10", "recall@50", "mrr", "dcg@10", "ndcg@10"}
