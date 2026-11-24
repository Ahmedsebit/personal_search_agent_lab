import pytest

from packages.eval.comparison import compare_reports
from packages.eval.models import ExperimentReport, QueryEvaluation


def _q(qid, text, ndcg, recall):
    metrics = {"precision@10": 0.1, "recall@10": 0.1, "recall@50": recall, "mrr": 0.2, "dcg@10": 1.0, "ndcg@10": ndcg}
    return QueryEvaluation(qid, text, "topic", [], metrics, 1.0)


def _report(name, queries):
    metrics = {key: sum(q.metrics[key] for q in queries) / len(queries) for key in queries[0].metrics}
    return ExperimentReport(name, name, len(queries), metrics, {}, {"p50_ms": 1.0, "p95_ms": 2.0}, queries)


def test_comparison_joins_by_query_id_not_position():
    control = _report("e001", [_q("q1", "rankng", 0.0, 0.0), _q("q2", "Atlas ranking", 1.0, 1.0)])
    treatment = _report("e002", [_q("q2", "Atlas ranking", 1.0, 1.0), _q("q1", "rankng", 0.8, 1.0)])
    result = compare_reports(control, treatment)
    rows = {row["query_id"]: row for row in result["per_query"]}
    assert rows["q1"]["deltas"]["recall@50"] == 1.0
    assert rows["q2"]["outcome"] == "unchanged"


def test_comparison_builds_targeted_and_none_cohorts():
    result = compare_reports(
        _report("e001", [_q("q1", "rankng", 0.0, 0.0), _q("q2", "Atlas ranking", 1.0, 1.0)]),
        _report("e002", [_q("q1", "rankng", 0.5, 0.5), _q("q2", "Atlas ranking", 1.0, 1.0)]),
    )
    assert result["cohort_summary"]["misspelling"]["query_count"] == 1
    assert result["cohort_summary"]["targeted"]["query_count"] == 1
    assert result["cohort_summary"]["none"]["query_count"] == 1


def test_acceptance_gates_use_preregistered_thresholds():
    result = compare_reports(
        _report("e001", [_q("q1", "rankng", 0.2, 0.2), _q("q2", "Atlas ranking", 0.8, 0.8)]),
        _report("e002", [_q("q1", "rankng", 0.3, 0.4), _q("q2", "Atlas ranking", 0.795, 0.795)]),
    )
    assert result["acceptance_gates"]["targeted_recall50_strictly_improves"]
    assert result["acceptance_gates"]["targeted_ndcg10_non_regression"]
    assert result["acceptance_gates"]["none_ndcg10_within_0.01"]
    assert result["acceptance_gates"]["quality_acceptance_pass"]


def test_comparison_rejects_mismatched_query_sets():
    with pytest.raises(ValueError):
        compare_reports(_report("a", [_q("q1", "x", 0.1, 0.1)]), _report("b", [_q("q2", "y", 0.1, 0.1)]))
