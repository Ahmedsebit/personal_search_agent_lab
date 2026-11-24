from packages.datasets.models import SearchQuery
from packages.eval.analysis import build_failure_taxonomy, metrics_by_difficulty
from packages.eval.models import ExperimentReport, QueryEvaluation


def _evaluation(query_id, scenario, ndcg, recall50):
    return QueryEvaluation(query_id, query_id, scenario, [], {"ndcg@10": ndcg, "recall@50": recall50}, 1.0)


def test_metrics_by_difficulty_groups_queries():
    report = ExperimentReport("x", "bm25", 2, {}, {}, {}, [_evaluation("q1", "topic", 0.2, 0.4), _evaluation("q2", "topic", 0.8, 1.0)])
    queries = [SearchQuery("q1", "one", "topic", "hard"), SearchQuery("q2", "two", "topic", "easy")]
    grouped = metrics_by_difficulty(report, queries)
    assert grouped["hard"]["ndcg@10"] == 0.2
    assert grouped["easy"]["recall@50"] == 1.0


def test_taxonomy_identifies_recency_failure():
    report = ExperimentReport("x", "bm25", 1, {}, {}, {}, [_evaluation("q1", "recency", 0.1, 0.8)])
    queries = [SearchQuery("q1", "latest Atlas update", "recency", "hard")]
    taxonomy = build_failure_taxonomy(report, queries)
    assert "temporal ordering not modeled" in taxonomy
