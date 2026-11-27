#!/usr/bin/env python3
"""U3 step 1 — build a BLIND human labelling sheet for the silver v2 benchmark.

Per scenario, sample queries (seed 20261124) and pool candidate emails from:
  - the top 5 of each supplied run file (what the systems actually retrieve)
  - up to 3 silver-relevant emails the runs missed
  - up to 3 random silver-non-relevant emails
The sheet shows the query and the email, never the silver grade. The key (silver grade, pool source)
goes to a separate file you should not open while labelling.

  PYTHONPATH=. python scripts/make_label_sheet.py --emails data/benchmark/emails.jsonl \
      --runs runs/e005/v2/control.json runs/e005/v2/treatment.json
      --out data/benchmark_v2/label_audit
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random

from packages.search.data.e003_corpus import (
    load_annotations,
    load_qrels,
    load_records,
    resolve_fields,
    timestamps_of,
    to_field_documents,
)

SEED = 20261124
SHEET_COLS = [
    "pair_id",
    "query_id",
    "scenario",
    "query",
    "reference_time",
    "doc_id",
    "date",
    "sender",
    "recipients",
    "subject",
    "attachment_names",
    "body_excerpt",
    "human_grade",
    "notes",
]


def build(
    ann, qrels, docs, ts, runs, queries_per_scenario=8, top=5, extra_pos=3, extra_neg=3, seed=SEED
):
    rng = random.Random(seed)
    by_id = {d["doc_id"]: d for d in docs}
    sheet, key = [], []
    for sc in sorted({a["scenario"] for a in ann}):
        qs = [a for a in ann if a["scenario"] == sc]
        rng.shuffle(qs)
        for a in qs[:queries_per_scenario]:
            q = a["query_id"]
            rel = qrels.get(q, {})
            pool = {}
            for name, r in runs.items():
                for d in (r.get(q, {}).get("ranked") or [])[:top]:
                    pool.setdefault(d, set()).add(f"run:{name}")
            missed = [d for d in sorted(rel) if d not in pool]
            rng.shuffle(missed)
            for d in missed[:extra_pos]:
                pool.setdefault(d, set()).add("silver_pos")
            negs = [d for d in sorted(by_id) if d not in rel and d not in pool]
            for d in rng.sample(negs, min(extra_neg, len(negs))):
                pool.setdefault(d, set()).add("random_neg")
            items = sorted(pool)
            rng.shuffle(items)
            for d in items:
                if d not in by_id:
                    continue
                e = by_id[d]
                pid = f"p{len(sheet):05d}"
                sheet.append(
                    {
                        "pair_id": pid,
                        "query_id": q,
                        "scenario": sc,
                        "query": a["query"],
                        "reference_time": a.get("reference_time", ""),
                        "doc_id": d,
                        "date": ts.get(d).isoformat() if ts.get(d) else "",
                        "sender": e["sender"],
                        "recipients": e["recipients"],
                        "subject": e["subject"],
                        "attachment_names": e["attachment_names"],
                        "body_excerpt": e["body"][:600].replace("\n", " "),
                        "human_grade": "",
                        "notes": "",
                    }
                )
                key.append(
                    {
                        "pair_id": pid,
                        "query_id": q,
                        "scenario": sc,
                        "doc_id": d,
                        "silver_grade": int(rel.get(d, 0)),
                        "sources": sorted(pool[d]),
                    }
                )
    return sheet, key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations", default="data/benchmark_v2/queries_v2.csv")
    ap.add_argument("--qrels", default="data/benchmark_v2/qrels_v2.jsonl")
    ap.add_argument("--emails", required=True)
    ap.add_argument("--field-map", default="{}")
    ap.add_argument("--runs", nargs="*", default=[])
    ap.add_argument("--queries-per-scenario", type=int, default=8)
    ap.add_argument("--out", default="data/benchmark_v2/label_audit")
    ap.add_argument(
        "--only-silver",
        action="store_true",
        help="label only rows whose qrels_type is silver (benchmark v3)",
    )
    ap.add_argument(
        "--exclude-scenarios",
        nargs="*",
        default=[],
        help="e.g. v2 scenarios already audited for E005",
    )
    a = ap.parse_args()
    recs = load_records(a.emails)
    fm = resolve_fields(recs, json.loads(a.field_map))
    runs = {
        os.path.splitext(os.path.basename(p))[0]: {
            q["query_id"]: q for q in json.load(open(p, encoding="utf-8"))["per_query"]
        }
        for p in a.runs
    }
    ann = load_annotations(a.annotations)
    if a.only_silver:
        ann = [x for x in ann if x.get("qrels_type", "silver") == "silver"]
    ann = [x for x in ann if x["scenario"] not in a.exclude_scenarios]
    sheet, key = build(
        ann,
        load_qrels(a.qrels),
        to_field_documents(recs, fm),
        timestamps_of(recs, fm),
        runs,
        a.queries_per_scenario,
    )
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "label_sheet.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLS)
        w.writeheader()
        w.writerows(sheet)
    with open(os.path.join(a.out, "label_key.jsonl"), "w", encoding="utf-8") as f:
        f.writelines(json.dumps(k) + "\n" for k in key)
    h = hashlib.sha256(open(a.annotations, "rb").read()).hexdigest()
    json.dump(
        {
            "queries_v2_sha256": h,
            "annotations_path": a.annotations,
            "seed": SEED,
            "n_pairs": len(sheet),
        },
        open(os.path.join(a.out, "sheet_manifest.json"), "w", encoding="utf-8"),
        indent=1,
    )
    from collections import Counter

    print(
        f"{len(sheet)} pairs → {a.out}/label_sheet.csv  per scenario: "
        f"{dict(Counter(r['scenario'] for r in sheet))}"
    )
    print(
        "Fill human_grade with 0 (not relevant), 1 (partly) or 2 (clearly relevant). "
        "Do not open label_key.jsonl while labelling."
    )


if __name__ == "__main__":
    main()
