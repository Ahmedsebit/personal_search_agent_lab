"""Cohort helpers and acceptance gates for E002b comparisons."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from statistics import mean

QUALITY_METRICS = (
    "precision_at_10",
    "recall_at_10",
    "recall_at_50",
    "mrr",
    "dcg_at_10",
    "ndcg_at_10",
)


@dataclass(frozen=True)
class QueryComparison:
    query_id: str
    query: str
    cohorts: tuple[str, ...]
    baseline: Mapping[str, float]
    treatment: Mapping[str, float]
    deltas: Mapping[str, float]


def e002b_cohort_labels(
    normalization_cohorts: Iterable[str],
    *,
    has_suppressed_alias: bool = False,
) -> tuple[str, ...]:
    """Build non-duplicated E002b cohort labels.

    - `alias_collision` identifies a suppressed alias in a protected full name.
    - `safe_alias` identifies alias expansion that remains eligible.
    - `other_targeted` covers non-alias normalization families.
    - `targeted` covers every changed/annotated query.
    - `none` is the untouched control.
    """
    families = tuple(dict.fromkeys(normalization_cohorts))
    labels: list[str] = list(families)

    collision = has_suppressed_alias or "alias_collision" in families
    safe_alias = "alias" in families and not collision
    other = any(family not in {"alias", "alias_collision"} for family in families)

    if collision:
        labels.append("alias_collision")
    if safe_alias:
        labels.append("safe_alias")
    if other:
        labels.append("other_targeted")

    if families or has_suppressed_alias:
        labels.append("targeted")
    else:
        labels.append("none")

    return tuple(dict.fromkeys(labels))


def compare_reports(
    baseline_rows: Sequence[Mapping[str, object]],
    treatment_rows: Sequence[Mapping[str, object]],
) -> tuple[QueryComparison, ...]:
    baseline = {str(row["query_id"]): row for row in baseline_rows}
    treatment = {str(row["query_id"]): row for row in treatment_rows}
    if baseline.keys() != treatment.keys():
        missing_treatment = sorted(baseline.keys() - treatment.keys())
        missing_baseline = sorted(treatment.keys() - baseline.keys())
        raise ValueError(
            "Query IDs do not align: "
            f"missing_treatment={missing_treatment}, "
            f"missing_baseline={missing_baseline}"
        )

    comparisons: list[QueryComparison] = []
    for query_id in sorted(baseline):
        control = baseline[query_id]
        candidate = treatment[query_id]
        control_metrics = _metrics(control)
        candidate_metrics = _metrics(candidate)
        raw_cohorts = candidate.get("cohorts", ())
        if not isinstance(raw_cohorts, (list, tuple)):
            raise ValueError("normalization cohorts must be a list or tuple")
        families = tuple(str(value) for value in raw_cohorts)
        suppressed = bool(candidate.get("suppressed_aliases", ()))
        labels = e002b_cohort_labels(
            families,
            has_suppressed_alias=suppressed,
        )
        deltas = {
            metric: candidate_metrics[metric] - control_metrics[metric]
            for metric in QUALITY_METRICS
        }
        comparisons.append(
            QueryComparison(
                query_id=query_id,
                query=str(candidate.get("query", control.get("query", ""))),
                cohorts=labels,
                baseline=control_metrics,
                treatment=candidate_metrics,
                deltas=deltas,
            )
        )
    return tuple(comparisons)


def summarize_cohorts(
    comparisons: Iterable[QueryComparison],
) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[QueryComparison]] = defaultdict(list)
    for comparison in comparisons:
        for cohort in comparison.cohorts:
            grouped[cohort].append(comparison)

    summary: dict[str, dict[str, float | int]] = {}
    for cohort, rows in sorted(grouped.items()):
        values: dict[str, float | int] = {"query_count": len(rows)}
        for metric in QUALITY_METRICS:
            values[f"delta_{metric}"] = mean(row.deltas[metric] for row in rows)
        summary[cohort] = values
    return summary


def evaluate_e002b_gates(
    cohort_summary: Mapping[str, Mapping[str, float | int]],
    comparisons: Iterable[QueryComparison],
    *,
    diagnostic_query_ids: Iterable[str] = (),
    guardrail: float = 0.01,
) -> dict[str, bool]:
    collision = cohort_summary.get("alias_collision", {})
    safe = cohort_summary.get("safe_alias", {})
    none = cohort_summary.get("none", {})

    by_id = {comparison.query_id: comparison for comparison in comparisons}
    diagnostics = [by_id[query_id] for query_id in diagnostic_query_ids]

    return {
        "alias_collision_ndcg_improves": _value(collision, "delta_ndcg_at_10") > 0,
        "alias_collision_recall50_non_regression": _value(collision, "delta_recall_at_50") >= 0,
        "safe_alias_recall50_retained": _value(safe, "delta_recall_at_50") >= -guardrail,
        "safe_alias_ndcg_retained": _value(safe, "delta_ndcg_at_10") >= -guardrail,
        "none_ndcg_within_guardrail": _value(none, "delta_ndcg_at_10") >= -guardrail,
        "none_recall50_within_guardrail": _value(none, "delta_recall_at_50") >= -guardrail,
        "diagnostic_queries_corrected": bool(diagnostics)
        and all(
            row.deltas["ndcg_at_10"] > 0 and row.deltas["recall_at_50"] >= 0 for row in diagnostics
        ),
    }


def _metrics(row: Mapping[str, object]) -> dict[str, float]:
    raw = row.get("metrics", row)
    assert isinstance(raw, Mapping)
    return {
        metric: float(raw[metric if metric in raw else metric.replace("_at_", "@")])
        for metric in QUALITY_METRICS
    }


def _value(values: Mapping[str, float | int], key: str) -> float:
    return float(values.get(key, float("-inf")))
