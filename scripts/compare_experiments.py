from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.eval.comparison import compare_reports
from packages.eval.models import ExperimentReport, QueryEvaluation


def load_report(path: Path) -> ExperimentReport:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ExperimentReport(
        name=payload["name"], retriever=payload["retriever"], query_count=payload["query_count"],
        aggregate_metrics=payload["aggregate_metrics"], scenario_metrics=payload["scenario_metrics"],
        latency=payload["latency"], per_query=[QueryEvaluation(**item) for item in payload["per_query"]],
    )


parser = argparse.ArgumentParser()
parser.add_argument("--control", type=Path, required=True)
parser.add_argument("--treatment", type=Path, required=True)
parser.add_argument("--output", type=Path, default=Path("experiments/results/e001-vs-e002-comparison.json"))
args = parser.parse_args()
comparison = compare_reports(load_report(args.control), load_report(args.treatment))
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(comparison, indent=2, sort_keys=True), encoding="utf-8")

md = args.output.with_suffix(".md")
lines = ["# E001 vs E002 comparison", "", f"Control: `{comparison['control']}`", f"Treatment: `{comparison['treatment']}`", "", "## Aggregate deltas (E002 - E001)", ""]
lines += [f"- {metric}: {value:+.4f}" for metric, value in comparison["aggregate_deltas"].items()]
lines += ["", "## Cohort deltas", ""]
for cohort, summary in comparison["cohort_summary"].items():
    lines.append(f"### {cohort} ({summary['query_count']} queries)")
    lines += [f"- {metric}: {value:+.4f}" for metric, value in summary["mean_deltas"].items()]
    lines.append(f"- outcomes: {summary['outcomes']}")
lines += ["", "## Acceptance gates", ""]
lines += [f"- {name}: {'PASS' if value else 'FAIL'}" for name, value in comparison["acceptance_gates"].items()]
lines += ["", "## Most changed queries by absolute NDCG@10 delta", ""]
changed = sorted(comparison["per_query"], key=lambda row: abs(row["deltas"]["ndcg@10"]), reverse=True)[:20]
for row in changed:
    lines.append(f"- `{row['query_id']}` {row['query']!r} [{','.join(row['cohorts'])}] {row['outcome']}: NDCG {row['deltas']['ndcg@10']:+.4f}; R@50 {row['deltas']['recall@50']:+.4f}")
md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {args.output} and {md}")
