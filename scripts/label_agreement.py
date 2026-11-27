#!/usr/bin/env python3
"""U3 step 3 — compare silver/LLM with human labels; write label_audit.json.

  PYTHONPATH=. python scripts/label_agreement.py --dir data/benchmark_v2/label_audit

E005 gates on v2 read label_audit.json: scenarios that are not VALIDATED are NOT EVALUABLE.
"""

from __future__ import annotations

import argparse
import csv
import json
import os

from packages.eval.labeling.agreement import audit


def fmt(x):
    return "—" if x is None else f"{x:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/benchmark_v2/label_audit")
    a = ap.parse_args()
    sheet = {
        r["pair_id"]: r
        for r in csv.DictReader(open(os.path.join(a.dir, "label_sheet.csv"), encoding="utf-8"))
    }
    key = {
        k["pair_id"]: k
        for k in map(json.loads, open(os.path.join(a.dir, "label_key.jsonl"), encoding="utf-8"))
    }
    llm_p = os.path.join(a.dir, "llm_labels.jsonl")
    llm = (
        {x["pair_id"]: x for x in map(json.loads, open(llm_p, encoding="utf-8"))}
        if os.path.exists(llm_p)
        else {}
    )
    rows = []
    for pid, r in sheet.items():
        g = r["human_grade"].strip()
        if g and g not in ("0", "1", "2"):
            raise SystemExit(f"{pid}: human_grade must be 0, 1 or 2 (got {g!r})")
        rows.append(
            {
                "scenario": r["scenario"],
                "human_grade": g,
                "silver_grade": key[pid]["silver_grade"],
                "llm_grade": ""
                if llm.get(pid, {}).get("llm_grade") is None
                else llm[pid]["llm_grade"],
            }
        )
    res = audit(rows)
    res["sheet_manifest"] = json.load(
        open(os.path.join(a.dir, "sheet_manifest.json"), encoding="utf-8")
    )
    json.dump(res, open(os.path.join(a.dir, "label_audit.json"), "w", encoding="utf-8"), indent=1)
    md = [
        "# Silver-label audit (U3)",
        "",
        f"Overall silver vs human: κ = {fmt(res['overall']['kappa_binary'])} "
        f"(reported only; each scenario is validated on its own), n = {res['overall']['n']}",
        "",
        "| Scenario | Pairs | κ (binary) | κ (quadratic) | "
        "Silver precision | Silver recall | Status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s, x in res["scenarios"].items():
        md.append(
            f"| {s} | {x['n']} | {fmt(x['kappa_binary'])} | {fmt(x['kappa_quadratic'])} | "
            f"{fmt(x['precision'])} | {fmt(x['recall'])} | **{x['status']}** |"
        )
    if res["llm"]:
        L = res["llm"]
        reuse = (
            "may label future benchmarks (LJ-1 PASS)"
            if L["LJ-1"]
            else "not reliable enough to label (LJ-1 FAIL)"
        )
        md += [
            "",
            f"LLM judge vs human (informational): κ = {fmt(L['kappa_binary'])}, n = {L['n']} → "
            + reuse,
        ]
    if os.path.exists(os.path.join(a.dir, "llm_cost.json")):
        c = json.load(open(os.path.join(a.dir, "llm_cost.json"), encoding="utf-8"))
        md.append(
            f"LLM judging cost: {c['total_tokens']} tokens vs "
            f"{c['baseline_total_tokens_est']} estimated without shared analysis "
            f"({c['analyse_calls']} emails analysed for {c['judge_calls']} judgments). "
            "Sharing pays off only when emails are judged several times."
        )
    open(os.path.join(a.dir, "label_audit.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
