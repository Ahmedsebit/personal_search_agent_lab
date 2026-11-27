#!/usr/bin/env python3
"""U3 step 2 (optional) — let an LLM judge grade the same sheet, with shared per-email analysis.

  python scripts/llm_label.py --provider mock
  For openai_compatible, configure LAB_LLM_ENDPOINT, LAB_LLM_API_KEY and LAB_LLM_MODEL.

Writes llm_labels.jsonl and llm_cost.json next to the sheet. Synthetic lab data only.
"""

from __future__ import annotations

import argparse
import csv
import json
import os

from packages.eval.labeling.llm_judge import SharedAnalysisJudge, make_provider


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default="data/benchmark_v2/label_audit/label_sheet.csv")
    ap.add_argument("--provider", default="mock", choices=["mock", "openai_compatible"])
    a = ap.parse_args()
    d = os.path.dirname(a.sheet)
    j = SharedAnalysisJudge(
        make_provider(a.provider), os.path.join(d, f"email_analysis.{a.provider}.jsonl")
    )
    out = []
    for r in csv.DictReader(open(a.sheet, encoding="utf-8")):
        doc = {
            "doc_id": r["doc_id"],
            "sender": r["sender"],
            "recipients": r["recipients"],
            "date": r["date"],
            "subject": r["subject"],
            "attachment_names": r["attachment_names"],
            "body": r["body_excerpt"],
        }
        res = j.judge(r["query"], doc, r.get("reference_time", ""))
        out.append({"pair_id": r["pair_id"], "llm_grade": res["grade"], "reason": res["reason"]})
    with open(os.path.join(d, "llm_labels.jsonl"), "w", encoding="utf-8") as f:
        f.writelines(json.dumps(x) + "\n" for x in out)
    cost = dict(j.cost_report(), provider=a.provider, n_pairs=len(out))
    json.dump(cost, open(os.path.join(d, "llm_cost.json"), "w", encoding="utf-8"), indent=1)
    s = cost["saving_vs_baseline_est"]
    print(
        f"{len(out)} pairs judged; {cost['analyse_calls']} email analyses, "
        f"{cost['judge_calls']} judgments; "
        f"tokens {cost['total_tokens']} vs no-sharing estimate {cost['baseline_total_tokens_est']}"
        + (f" ({s:.0%} saving)" if s is not None else "")
    )


if __name__ == "__main__":
    main()
