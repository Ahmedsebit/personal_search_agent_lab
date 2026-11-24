#!/usr/bin/env python3
"""Evaluate all E003 preregistered gates from the four run files.

  PYTHONPATH=. python scripts/compare_e003.py --runs runs/e003 \
      --annotations docs/experiments/e003/e003-query-annotations.csv \
      --out docs/experiments/e003/results
"""
from __future__ import annotations

import argparse, json, os
from statistics import mean


from packages.search.data.e003_corpus import load_annotations
from packages.eval import e003_comparison as C


def load(path):
    d = json.load(open(path))
    return d, {q["query_id"]: q for q in d["per_query"]}


def latency(run):
    xs = sorted(q["latency_ms"] for q in run.values())
    return {"p50_ms": xs[len(xs) // 2], "p95_ms": xs[int(0.95 * (len(xs) - 1))]}


def fmt(x):
    return "—" if x is None else (f"{x:+.4f}" if isinstance(x, float) else str(x))


def gate_rows(gates):
    rows = []
    for gid, g in gates.items():
        parts = g.get("parts") if isinstance(g.get("parts"), list) and g["parts"] and "metric" in g["parts"][0] else [g]
        for p in parts:
            if "metric" in p:
                ci = p.get("ci95")
                rows.append(f"| {gid} | {p['cohort']} {p['metric']} {p['requirement']} | {fmt(p['delta'])} | "
                            f"{fmt(p['delta_dedup'])} | {'[' + ', '.join(f'{c:+.4f}' for c in ci) + ']' if ci else '—'} | **{p['status']}** |")
            else:
                rows.append(f"| {gid} | see JSON | — | — | — | **{g['status']}** |")
                break
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/e003")
    ap.add_argument("--annotations", default="docs/experiments/e003/e003-query-annotations.csv")
    ap.add_argument("--out", default="docs/experiments/e003/results")
    a = ap.parse_args()
    ann = load_annotations(a.annotations)
    os.makedirs(a.out, exist_ok=True)
    meta_c, ctrl = load(os.path.join(a.runs, "control.json"))
    smoke = bool(meta_c.get("smoke"))
    if meta_c.get("control_parity") and not meta_c["control_parity"]["pass"] and not smoke:
        raise SystemExit("Control parity failed; gates are not valid.")
    runs = {}
    for arm in ("e003_f", "e003_t", "e003_ft"):
        p = os.path.join(a.runs, f"{arm}.json")
        if os.path.exists(p):
            runs[arm] = load(p)[1]
    report, md = {"control_latency": latency(ctrl), "smoke": smoke}, ["# E003 results" + (" — SMOKE RUN, NOT VALID EVIDENCE" if smoke else ""), "",
        "Query-weighted delta is primary; de-duplicated delta is the sensitivity check. "
        "A pass that holds only query-weighted is **PASS (fragile)**.", ""]
    verdicts = {}
    for arm, fn, name in (("e003_f", C.gates_f, "E003-F"), ("e003_t", C.gates_t, "E003-T")):
        if arm not in runs:
            md += [f"## {name}", "", "Not run (NOT EVALUABLE or pending).", ""]
            continue
        table, gates = fn(ctrl, runs[arm], ann)
        verdicts[arm] = C.arm_verdict(gates)
        report[arm] = {"cohorts": table, "gates": gates, "verdict": verdicts[arm], "latency": latency(runs[arm])}
        json.dump(report[arm], open(os.path.join(a.out, f"{arm.replace('_','-')}-vs-e002b-comparison.json"), "w"), indent=1)
        md += [f"## {name} vs E002b — {verdicts[arm]['verdict']}", "",
               "| Gate | Requirement | Δ (query) | Δ (dedup) | 95% CI | Result |", "| --- | --- | --- | --- | --- | --- |",
               *gate_rows(gates), ""]
    if all(k in runs for k in ("e003_f", "e003_t", "e003_ft")):
        table, gates, inter = C.gates_ft(ctrl, runs["e003_f"], runs["e003_t"], runs["e003_ft"], ann)
        verdicts["e003_ft"] = C.arm_verdict(gates)
        report["e003_ft"] = {"cohorts": table, "gates": gates, "interaction": inter,
                             "verdict": verdicts["e003_ft"], "latency": latency(runs["e003_ft"])}
        json.dump(report["e003_ft"], open(os.path.join(a.out, "e003-ft-vs-e002b-comparison.json"), "w"), indent=1)
        json.dump({"interaction": inter, "FT-B": gates["FT-B"]}, open(os.path.join(a.out, "e003-ft-vs-f-and-t.json"), "w"), indent=1)
        md += [f"## E003-FT vs E002b — {verdicts['e003_ft']['verdict']}", "",
               "| Gate | Requirement | Δ (query) | Δ (dedup) | 95% CI | Result |", "| --- | --- | --- | --- | --- | --- |",
               *gate_rows(gates), "", "### Interaction (NDCG@10)", "", "| Cohort | I | Label |", "| --- | --- | --- |",
               *[f"| {c} | {v['I']:+.4f} | {v['label']} |" for c, v in inter.items()], ""]
        report["decision"] = C.final_decision(verdicts["e003_f"], verdicts["e003_t"], verdicts["e003_ft"])
        md += ["## Decision", "", report["decision"], ""]
    md += ["## Mechanism predictions (not gated)", "", "| Arm | Cohort | ΔNDCG@10 | ΔRecall@50 | improved/regressed/unchanged |",
           "| --- | --- | --- | --- | --- |"]
    for arm in ("e003_f", "e003_t", "e003_ft"):
        if arm in report:
            for c in ("sub_f_ordering", "sub_t_ordering", "sub_paraphrase_recall_limited", "person"):
                r = report[arm]["cohorts"].get(c)
                if r:
                    md.append(f"| {arm} | {c} | {fmt(r['ndcg@10']['delta'])} | {fmt(r['recall@50']['delta'])} | "
                              f"{r['improved']}/{r['regressed']}/{r['unchanged']} |")
    json.dump(report, open(os.path.join(a.out, "e003-results.json"), "w"), indent=1, default=str)
    open(os.path.join(a.out, "e003-results.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
