#!/usr/bin/env python3
"""U1 — describe how consistently any run handles reworded queries (no gates, just the numbers).

python scripts/robustness_report.py --run runs/e004/pt/control.json
Add --run runs/e004/pt/treatment.json to compare both arms.
"""

from __future__ import annotations

import argparse
import json

from packages.eval.robustness import summarize
from packages.search.data.e003_corpus import load_annotations


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True)
    ap.add_argument("--annotations", default="data/benchmark_pt/queries_pt.csv")
    a = ap.parse_args()
    ann = load_annotations(a.annotations)
    print(
        "| Run | Families | Mean abs gap | Mean worst | Mean paraphrase | "
        "Top-10 overlap | Inconsistent (>0.10) |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for p in a.run:
        d = json.load(open(p, encoding="utf-8"))
        s = summarize({q["query_id"]: q for q in d["per_query"]}, ann)
        if not s["n_families"]:
            print(f"| {p} | 0 | — | — | — | — | — |")
            continue
        print(
            f"| {d['experiment']} {d['arm']} | {s['n_families']} | "
            f"{s['mean_abs_gap']:.4f} | {s['mean_worst']:.4f} | "
            f"{s['mean_para']:.4f} | {s['mean_overlap']:.4f} | {s['inconsistent_share']:.0%} |"
        )


if __name__ == "__main__":
    main()
