#!/usr/bin/env python3
"""Evaluate an E004–E008 preregistration's gates from its run files.

PYTHONPATH=. python scripts/evaluate_prereg.py --prereg docs/experiments/e004/e004-gates.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import yaml

from packages.eval.labeling.agreement import apply_label_audit
from packages.eval.prereg_gates import component_verdicts, evaluate, verdict
from packages.search.data.e003_corpus import load_annotations


def f(x):
    return "-" if x is None else f"{x:+.4f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    p = yaml.safe_load(Path(a.prereg).read_text(encoding="utf-8"))
    out = a.out or os.path.join(os.path.dirname(a.prereg), "results")
    os.makedirs(out, exist_ok=True)
    md = [f"# {p['experiment']} results", ""]
    report = {"experiment": p["experiment"], "benchmarks": {}}
    smoke = False
    for bench, spec in p["evaluations"].items():
        if spec.get("optional") and not all(os.path.exists(x) for x in spec["runs"].values()):
            md += [
                f"## Benchmark {bench}",
                "",
                "Optional evaluation skipped (run files not present).",
                "",
            ]
            continue
        runs, timing = {}, {}
        benchmark_smoke = False
        for name, path in spec["runs"].items():
            d = json.loads(Path(path).read_text(encoding="utf-8"))
            smoke |= bool(d.get("smoke"))
            benchmark_smoke |= bool(d.get("smoke"))
            if d.get("control_parity") and not d["control_parity"]["pass"] and not d.get("smoke"):
                raise SystemExit(f"{path}: control parity failed; results invalid")
            runs[name] = {q["query_id"]: q for q in d["per_query"]}
            timing[name] = d.get("timing")
        ann = load_annotations(spec["annotations"])
        gates = evaluate(dict(p, gates=spec["gates"]), runs, ann, timing)
        if spec.get("label_audit"):
            audit_obj = None
            reason = "no label audit found; run the U3 steps"
            audit_path = Path(spec["label_audit"])
            if audit_path.exists():
                audit_obj = json.loads(audit_path.read_text(encoding="utf-8"))
                expected = hashlib.sha256(Path(spec["annotations"]).read_bytes()).hexdigest()
                if audit_obj.get("sheet_manifest", {}).get("queries_v2_sha256") != expected:
                    audit_obj = None
                    reason = "label audit was made for a different benchmark file"
            if audit_obj is not None or not benchmark_smoke:
                apply_label_audit(gates, p["cohorts"], audit_obj, reason)
        report["benchmarks"][bench] = gates
        md += [
            f"## Benchmark {bench}",
            "",
            "| Gate | Hypothesis | Cohort (n) | Metric | Requirement "
            "| Delta (query / family) | Delta (dedup) | 95% CI | Result |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for g in gates.values():
            req = {
                "gt0": "> 0",
                "guard": f">= -{p.get('epsilon', 0.01)}",
                "equal": "= 0",
                "invariant_lists": "identical top-50",
                "per_query_retain": f"each >= ctrl - {p.get('epsilon', 0.01)}",
                "family_gt0": f"{g.get('stat')} better",
                "family_guard": f"{g.get('stat')} not worse by > {p.get('epsilon', 0.01)}",
                "latency_budget": "latency budget",
                "gain_per_latency": "gain per +100 ms",
            }[g["kind"]]
            definition = next(x for x in spec["gates"] if x["id"] == g["id"])
            delta, metric, n, status = g.get("delta"), g["metric"], g["n"], g["status"]
            if g["kind"] == "latency_budget":
                req = f"{definition.get('stat', 'p95')}: " + ", ".join(
                    f"{k} {definition[k]}"
                    for k in ("max_ms", "max_added_ms", "max_ratio")
                    if k in definition
                )
                delta, metric = g.get("added_ms"), "latency (ms)"
                if "treatment_ms" in g:
                    status += f"; {g['control_ms']:.1f} -> {g['treatment_ms']:.1f} ms"
            elif g["kind"] == "gain_per_latency":
                req = f">= {definition['min_gain_per_100ms']} {metric} per +100 ms p50"
                delta = g.get("gain_per_100ms")
            if g.get("informational"):
                status += " (informational)"
            if "n_families" in g:
                n = f"{g['n_families']} families"
            ci = g.get("ci95")
            md.append(
                f"| {g['id']} | {g['hypothesis']} | {g['cohort']} ({n}) | "
                f"{metric} | {req} | {f(delta)} | {f(g.get('delta_dedup'))} | "
                f"{'[' + ', '.join(f'{c:+.4f}' for c in ci) + ']' if ci else '-'} "
                f"| **{status}** |"
            )
        md.append("")
    allg = {f"{b}:{k}": v for b, gs in report["benchmarks"].items() for k, v in gs.items()}
    report["verdict"] = verdict(allg)
    report["component_verdicts"] = component_verdicts(allg)
    report["smoke"] = smoke
    md.insert(
        1,
        ("**SMOKE RUN — NOT VALID EVIDENCE**\n\n" if smoke else "")
        + f"**Verdict:** {report['verdict']}\n"
        + "".join(f"\n- Component `{c}`: {v}" for c, v in report["component_verdicts"].items())
        + "\n",
    )
    Path(out, f"{p['experiment'].lower()}-results.json").write_text(
        json.dumps(report, indent=1, default=str), encoding="utf-8"
    )
    Path(out, f"{p['experiment'].lower()}-results.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8"
    )
    print("\n".join(md))


if __name__ == "__main__":
    main()
