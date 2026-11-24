import json
import runpy
import sys
from pathlib import Path

import pytest

from packages.eval.e002b_comparison import (
    compare_reports,
    e002b_cohort_labels,
    evaluate_e002b_gates,
    summarize_cohorts,
)

METRICS_ZERO = {
    "precision_at_10": 0.0,
    "recall_at_10": 0.0,
    "recall_at_50": 0.0,
    "mrr": 0.0,
    "dcg_at_10": 0.0,
    "ndcg_at_10": 0.0,
}


def row(query_id, query, *, cohorts=(), suppressed=(), **metrics):
    values = dict(METRICS_ZERO)
    values.update(metrics)
    return {
        "query_id": query_id,
        "query": query,
        "cohorts": cohorts,
        "suppressed_aliases": suppressed,
        "metrics": values,
    }


def test_cohort_labels_distinguish_collision_safe_alias_and_none() -> None:
    assert e002b_cohort_labels(("alias_collision",), has_suppressed_alias=True) == (
        "alias_collision",
        "targeted",
    )
    assert e002b_cohort_labels(("alias",)) == (
        "alias",
        "safe_alias",
        "targeted",
    )
    assert e002b_cohort_labels(()) == ("none",)


def test_other_targeted_cohort_is_added_without_duplicate_labels() -> None:
    labels = e002b_cohort_labels(("initials", "alias", "initials"))

    assert labels == (
        "initials",
        "alias",
        "safe_alias",
        "other_targeted",
        "targeted",
    )


def test_reports_join_by_query_id_not_position() -> None:
    baseline = [
        row("q1", "collision", ndcg_at_10=0.1),
        row("q2", "safe", ndcg_at_10=0.8),
    ]
    treatment = [
        row("q2", "safe", cohorts=("alias",), ndcg_at_10=0.8),
        row(
            "q1",
            "collision",
            cohorts=("alias_collision",),
            suppressed=({"alias": "ali"},),
            ndcg_at_10=0.7,
        ),
    ]

    comparisons = compare_reports(baseline, treatment)

    assert [item.query_id for item in comparisons] == ["q1", "q2"]
    assert comparisons[0].deltas["ndcg_at_10"] == pytest.approx(0.6)


def test_mismatched_query_ids_are_rejected() -> None:
    with pytest.raises(ValueError):
        compare_reports(
            [row("q1", "one")],
            [row("q2", "two")],
        )


@pytest.mark.parametrize("baseline_native", [False, True])
@pytest.mark.parametrize("treatment_native", [False, True])
def test_reports_accept_runner_metric_names(baseline_native: bool, treatment_native: bool) -> None:
    baseline = row("q1", "collision", ndcg_at_10=0.1, recall_at_50=0.3)
    treatment = row(
        "q1", "collision", cohorts=("alias_collision",), ndcg_at_10=0.7, recall_at_50=0.8
    )
    for report_row, native in [(baseline, baseline_native), (treatment, treatment_native)]:
        if native:
            report_row["metrics"] = {
                name.replace("_at_", "@"): value for name, value in report_row["metrics"].items()
            }

    (comparison,) = compare_reports([baseline], [treatment])

    assert comparison.deltas["ndcg_at_10"] == pytest.approx(0.6)
    assert comparison.deltas["recall_at_50"] == pytest.approx(0.5)
    assert comparison.deltas["mrr"] == 0.0
    assert set(comparison.deltas) == set(METRICS_ZERO)


def test_missing_metric_is_not_defaulted() -> None:
    incomplete = row("q1", "budget")
    del incomplete["metrics"]["ndcg_at_10"]

    with pytest.raises(KeyError):
        compare_reports([row("q1", "budget")], [incomplete])


def test_cli_rejects_the_same_report_for_both_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "compare_e002b.py"
    report_path = tmp_path / "report.json"
    output_path = tmp_path / "comparison.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(script),
            "--e002",
            str(report_path),
            "--e002b",
            str(report_path),
            "--output",
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(script), run_name="__main__")

    assert error.value.code == 2
    assert "use the E002 baseline report for --e002" in capsys.readouterr().err
    assert not output_path.exists()


@pytest.mark.parametrize("invalid_input", ["--e002", "--e002b"])
def test_cli_rejects_comparison_artifacts_as_inputs(
    invalid_input: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "compare_e002b.py"
    baseline = tmp_path / "e002.json"
    treatment = tmp_path / "e002b.json"
    output = tmp_path / "comparison.json"
    for path in (baseline, treatment):
        path.write_text(json.dumps({"per_query": [row("q1", "budget")]}), encoding="utf-8")
    invalid_path = baseline if invalid_input == "--e002" else treatment
    invalid_path.write_text(
        json.dumps({"comparison": "E002b-minus-E002", "per_query": []}), encoding="utf-8"
    )
    output.write_text("existing output", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [str(script), "--e002", str(baseline), "--e002b", str(treatment), "--output", str(output)],
    )

    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(script), run_name="__main__")

    assert error.value.code == 2
    assert "is a comparison output, not an experiment report" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "existing output"


@pytest.mark.parametrize("overwritten_input", ["--e002", "--e002b"])
def test_cli_rejects_output_overwriting_an_input(
    overwritten_input: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "compare_e002b.py"
    baseline = tmp_path / "e002.json"
    treatment = tmp_path / "e002b.json"
    for path in (baseline, treatment):
        path.write_text("original input", encoding="utf-8")
    output = baseline if overwritten_input == "--e002" else treatment
    monkeypatch.setattr(
        sys,
        "argv",
        [str(script), "--e002", str(baseline), "--e002b", str(treatment), "--output", str(output)],
    )

    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(script), run_name="__main__")

    assert error.value.code == 2
    assert "--output must be different from both input reports" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "original input"


def test_cohort_summary_and_all_preregistered_gates() -> None:
    baseline = [
        row("q1", "emails from Fatima Ali", ndcg_at_10=0.1, recall_at_50=0.3),
        row("q2", "emails from Ali", ndcg_at_10=0.8, recall_at_50=0.8),
        row("q3", "latest Atlas ranking", ndcg_at_10=0.7, recall_at_50=0.7),
    ]
    treatment = [
        row(
            "q1",
            "emails from Fatima Ali",
            cohorts=("alias_collision",),
            suppressed=({"alias": "ali"},),
            ndcg_at_10=0.9,
            recall_at_50=0.4,
        ),
        row(
            "q2",
            "emails from Ali",
            cohorts=("alias",),
            ndcg_at_10=0.795,
            recall_at_50=0.795,
        ),
        row(
            "q3",
            "latest Atlas ranking",
            ndcg_at_10=0.7,
            recall_at_50=0.7,
        ),
    ]

    comparisons = compare_reports(baseline, treatment)
    summary = summarize_cohorts(comparisons)
    gates = evaluate_e002b_gates(
        summary,
        comparisons,
        diagnostic_query_ids=("q1",),
    )

    assert summary["alias_collision"]["query_count"] == 1
    assert summary["safe_alias"]["query_count"] == 1
    assert summary["none"]["query_count"] == 1
    assert all(gates.values())
