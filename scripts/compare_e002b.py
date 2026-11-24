#!/usr/bin/env python3
"""Compare E002b against E002 and optionally E001."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.eval.e002b_comparison import (
    compare_reports,
    evaluate_e002b_gates,
    summarize_cohorts,
)


def load_rows(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        if "comparison" in payload:
            raise ValueError(
                f"{path} is a comparison output, not an experiment report; "
                "use an experiment report containing absolute per-query metrics"
            )
        rows = payload.get("queries", payload.get("per_query"))
    else:
        rows = payload
    if not isinstance(rows, list) or not all(
        isinstance(row, dict) and "query_id" in row for row in rows
    ):
        raise ValueError(f"{path} must contain a list of per-query experiment results")
    if any("deltas" in row and "metrics" not in row for row in rows):
        raise ValueError(f"{path} contains comparison deltas, not absolute per-query metrics")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--e002", type=Path, required=True)
    parser.add_argument("--e002b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostic-query-id", action="append", default=[])
    args = parser.parse_args()

    if args.e002.resolve() == args.e002b.resolve():
        parser.error(
            "--e002 and --e002b must point to different reports; "
            "use the E002 baseline report for --e002"
        )

    if args.output.resolve() in (args.e002.resolve(), args.e002b.resolve()):
        parser.error("--output must be different from both input reports")

    try:
        baseline_rows = load_rows(args.e002)
        treatment_rows = load_rows(args.e002b)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    comparisons = compare_reports(baseline_rows, treatment_rows)
    cohorts = summarize_cohorts(comparisons)
    gates = evaluate_e002b_gates(
        cohorts,
        comparisons,
        diagnostic_query_ids=args.diagnostic_query_id,
    )
    payload = {
        "comparison": "E002b-minus-E002",
        "cohorts": cohorts,
        "acceptance_gates": gates,
        "quality_acceptance": all(gates.values()),
        "per_query": [
            {
                "query_id": row.query_id,
                "query": row.query,
                "cohorts": list(row.cohorts),
                "deltas": dict(row.deltas),
            }
            for row in comparisons
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
