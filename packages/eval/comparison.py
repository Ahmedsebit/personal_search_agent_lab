from __future__ import annotations

from packages.eval.models import ExperimentReport


def metric_deltas(control: ExperimentReport, treatment: ExperimentReport) -> dict[str, float]:
    return {name: treatment.aggregate_metrics[name] - value for name, value in control.aggregate_metrics.items()}
