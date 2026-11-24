from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from packages.datasets.loader import load_dataset
from packages.eval.analysis import analyze_report
from packages.eval.models import ExperimentReport, QueryEvaluation

parser = argparse.ArgumentParser()
parser.add_argument("--report", type=Path, default=Path("experiments/results/e001-bm25-baseline.json"))
parser.add_argument("--dataset", type=Path, default=Path("datasets"))
parser.add_argument("--output", type=Path, default=Path("experiments/results/e001-bm25-analysis-v2.json"))
args = parser.parse_args()

payload = json.loads(args.report.read_text(encoding="utf-8"))
report = ExperimentReport(
    name=payload["name"], retriever=payload["retriever"], query_count=payload["query_count"],
    aggregate_metrics=payload["aggregate_metrics"], scenario_metrics=payload["scenario_metrics"],
    latency=payload["latency"], per_query=[QueryEvaluation(**item) for item in payload["per_query"]],
)
_, queries, _ = load_dataset(args.dataset)
analysis = analyze_report(report, queries)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
md = args.output.with_suffix(".md")
lines = ["# E001 BM25 analysis", "", "## Aggregate metrics", ""]
lines += [f"- {key}: {value:.4f}" for key, value in analysis["aggregate_metrics"].items()]
lines += ["", "## Latency", ""] + [f"- {key}: {value:.3f}" for key, value in analysis["latency"].items()]
for heading, key in (("Scenario breakdown", "scenario_metrics"), ("Difficulty breakdown", "difficulty_metrics")):
    lines += ["", f"## {heading}", ""]
    for group, metrics in analysis[key].items():
        lines.append(f"### {group}")
        lines += [f"- {name}: {value:.4f}" for name, value in metrics.items()]
lines += ["", "## Failure taxonomy", ""]
for label, values in analysis["failure_taxonomy"].items():
    lines.append(f"- **{label}**: {values['count']} queries; mean NDCG@10 {values['mean_ndcg@10']:.4f}; mean Recall@50 {values['mean_recall@50']:.4f}")
lines += ["", "## Worst queries", ""]
for item in analysis["worst_queries"]:
    lines.append(f"- `{item['query_id']}` [{item['scenario']}/{item['difficulty']}] {item['query']!r}: NDCG@10 {item['metrics']['ndcg@10']:.4f}; labels: {', '.join(item['failure_labels'])}")
md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {args.output} and {md}")
