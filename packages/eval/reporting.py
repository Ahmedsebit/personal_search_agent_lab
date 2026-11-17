from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from packages.eval.models import ExperimentReport


def write_report(report: ExperimentReport, output_dir: Path, config: dict[str, object]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{report.name}.json"
    md_path = output_dir / f"{report.name}.md"
    payload = asdict(report); payload["config"] = config
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    worst = sorted(report.per_query, key=lambda item: item.metrics["ndcg@10"])[:20]
    lines = [f"# Experiment: {report.name}", "", f"Retriever: `{report.retriever}`", f"Queries: {report.query_count}", "", "## Aggregate metrics", ""]
    lines += [f"- {key}: {value:.4f}" for key, value in report.aggregate_metrics.items()]
    lines += ["", "## Latency", "", *[f"- {key}: {value:.3f}" for key, value in report.latency.items()], "", "## Scenario metrics", ""]
    for scenario, metrics in sorted(report.scenario_metrics.items()):
        lines.append(f"### {scenario}"); lines += [f"- {key}: {value:.4f}" for key, value in metrics.items()]
    lines += ["", "## Worst 20 queries by NDCG@10", ""]
    lines += [f"- `{item.query_id}` [{item.scenario}] {item.query!r}: {item.metrics['ndcg@10']:.4f}" for item in worst]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
