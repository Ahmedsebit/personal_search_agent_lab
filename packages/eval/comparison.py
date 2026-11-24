from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from packages.eval.models import ExperimentReport, QueryEvaluation
from packages.search.query.normalization import normalize_query

QUALITY_METRICS = ("precision@10", "recall@10", "recall@50", "mrr", "dcg@10", "ndcg@10")


def metric_deltas(control: ExperimentReport, treatment: ExperimentReport) -> dict[str, float]:
    """Treatment minus control for aggregate metrics shared by both reports."""
    return {
        name: treatment.aggregate_metrics[name] - control.aggregate_metrics[name]
        for name in control.aggregate_metrics
        if name in treatment.aggregate_metrics
    }


def _query_index(report: ExperimentReport) -> dict[str, QueryEvaluation]:
    return {item.query_id: item for item in report.per_query}


def _cohort_labels(query: str) -> tuple[str, ...]:
    cohorts = normalize_query(query).cohorts
    if cohorts == ("none",):
        return cohorts
    labels = list(cohorts) + ["targeted"]
    if len(cohorts) > 1:
        labels.append("multiple")
    return tuple(labels)


def compare_reports(control: ExperimentReport, treatment: ExperimentReport) -> dict[str, object]:
    """Join reports by query ID and summarize E002-minus-E001 deltas."""
    control_by_id = _query_index(control)
    treatment_by_id = _query_index(treatment)
    if set(control_by_id) != set(treatment_by_id):
        missing_treatment = sorted(set(control_by_id) - set(treatment_by_id))
        missing_control = sorted(set(treatment_by_id) - set(control_by_id))
        raise ValueError(
            f"query IDs differ; missing in treatment={missing_treatment[:5]}, "
            f"missing in control={missing_control[:5]}"
        )

    rows: list[dict[str, object]] = []
    for query_id in sorted(control_by_id):
        before = control_by_id[query_id]
        after = treatment_by_id[query_id]
        if before.query != after.query:
            raise ValueError(f"query text differs for {query_id}")
        deltas = {
            metric: after.metrics[metric] - before.metrics[metric]
            for metric in QUALITY_METRICS
            if metric in before.metrics and metric in after.metrics
        }
        ndcg_delta = deltas.get("ndcg@10", 0.0)
        recall_delta = deltas.get("recall@50", 0.0)
        epsilon = 1e-12
        if ndcg_delta > epsilon or recall_delta > epsilon:
            outcome = "improved"
        elif ndcg_delta < -epsilon or recall_delta < -epsilon:
            outcome = "regressed"
        else:
            outcome = "unchanged"
        rows.append({
            "query_id": query_id,
            "query": before.query,
            "scenario": before.scenario,
            "cohorts": list(_cohort_labels(before.query)),
            "control_metrics": before.metrics,
            "treatment_metrics": after.metrics,
            "deltas": deltas,
            "outcome": outcome,
        })

    cohort_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for cohort in row["cohorts"]:
            cohort_rows[str(cohort)].append(row)

    cohort_summary: dict[str, dict[str, object]] = {}
    for cohort, items in sorted(cohort_rows.items()):
        cohort_summary[cohort] = {
            "query_count": len(items),
            "mean_deltas": {
                metric: mean(float(item["deltas"][metric]) for item in items)
                for metric in QUALITY_METRICS
            },
            "outcomes": dict(Counter(str(item["outcome"]) for item in items)),
        }

    scenario_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        scenario_rows[str(row["scenario"])].append(row)
    scenario_summary = {
        scenario: {
            metric: mean(float(item["deltas"][metric]) for item in items)
            for metric in QUALITY_METRICS
        }
        for scenario, items in sorted(scenario_rows.items())
    }

    latency_delta = {
        name: treatment.latency[name] - control.latency[name]
        for name in control.latency
        if name in treatment.latency
    }

    none = cohort_summary.get("none", {"mean_deltas": {}})
    targeted = cohort_summary.get("targeted", {"mean_deltas": {}})
    none_deltas = none["mean_deltas"]
    targeted_deltas = targeted["mean_deltas"]
    gates = {
        "targeted_recall50_strictly_improves": targeted_deltas.get("recall@50", 0.0) > 0.0,
        "targeted_ndcg10_non_regression": targeted_deltas.get("ndcg@10", 0.0) >= 0.0,
        "none_ndcg10_within_0.01": none_deltas.get("ndcg@10", 0.0) >= -0.01,
        "none_recall50_within_0.01": none_deltas.get("recall@50", 0.0) >= -0.01,
    }
    gates["quality_acceptance_pass"] = all(gates.values())

    return {
        "control": control.name,
        "treatment": treatment.name,
        "aggregate_deltas": metric_deltas(control, treatment),
        "latency_deltas_ms": latency_delta,
        "cohort_summary": cohort_summary,
        "scenario_delta_summary": scenario_summary,
        "acceptance_gates": gates,
        "per_query": rows,
    }
