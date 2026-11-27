#!/usr/bin/env python3
"""U1 — build the paraphrase-twin benchmark ("pt") from the frozen v1 benchmark.

For each unique v1 query containing a term from either side of the frozen E004 lexicon,
make a twin by swapping that term. Both variants inherit the SOURCE query's gold qrels,
so a family's two variants ask for the same thing and are judged against the same answers.

  python scripts/build_paraphrase_twins.py --qrels datasets/benchmarks/judgments.jsonl

Preregistered assumption: a lexicon swap preserves intent, so the source qrels apply.
The lexicon is benchmark-derived (see E004), so E004 on this
benchmark is reported as informational only: it closes the gap by construction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter

from packages.search.data.e003_corpus import load_annotations, load_qrels
from packages.search.query.synonym_expansion import LEXICON

V1 = "docs/experiments/e003/e003-query-annotations.csv"
KEEP = ["scenario", "e003_cohort", "temporal_explicit", "field_sensitive", "e002b_diagnostic"]
COLS = [
    "query_id",
    "query",
    "family_id",
    "variant",
    "origin",
    "canonical_term",
    "paraphrase_term",
    "source_query_id",
    "source_query",
] + KEEP


def find_term(q: str):
    low = q.lower()
    for para, canon in sorted(LEXICON.items(), key=lambda kv: -len(kv[0])):
        for term, kind in ((para, "paraphrase"), (canon, "canonical")):
            if re.search(r"(?<![a-z0-9-])" + re.escape(term) + r"(?![a-z0-9-])", low):
                return para, canon, kind
    return None


def swap(q: str, src: str, dst: str) -> str:
    return re.sub(r"(?i)(?<![a-z0-9-])" + re.escape(src) + r"(?![a-z0-9-])", dst, q, count=1)


def build(ann, qrels):
    seen, rows, out_qrels = set(), [], []
    for a in ann:
        key = a["query"].strip().lower()
        if key in seen or a["query_id"] not in qrels:
            continue
        hit = find_term(a["query"])
        if not hit:
            continue
        seen.add(key)
        para, canon, kind = hit
        fam = f"fam-{len(rows) // 2:03d}"
        texts = {
            "canonical": a["query"] if kind == "canonical" else swap(a["query"], para, canon),
            "paraphrase": a["query"] if kind == "paraphrase" else swap(a["query"], canon, para),
        }
        for variant in ("canonical", "paraphrase"):
            qid = f"pt-{len(rows):04d}"
            row = {
                "query_id": qid,
                "query": texts[variant],
                "family_id": fam,
                "variant": variant,
                "origin": f"{kind}_original",
                "canonical_term": canon,
                "paraphrase_term": para,
                "source_query_id": a["query_id"],
                "source_query": a["query"],
            }
            row.update({k: a.get(k, "") for k in KEEP})
            rows.append(row)
            out_qrels += [
                {"query_id": qid, "doc_id": d, "grade": g}
                for d, g in sorted(qrels[a["query_id"]].items())
            ]
    return rows, out_qrels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations", default=V1)
    ap.add_argument("--qrels", required=True, help="the frozen v1 gold qrels")
    ap.add_argument("--out", default="data/benchmark_pt")
    a = ap.parse_args()
    rows, qr = build(load_annotations(a.annotations), load_qrels(a.qrels))
    os.makedirs(a.out, exist_ok=True)
    qp, rp = os.path.join(a.out, "queries_pt.csv"), os.path.join(a.out, "qrels_pt.jsonl")
    with open(qp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    with open(rp, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in qr)
    h = hashlib.sha256(open(qp, "rb").read()).hexdigest()
    fams = len(rows) // 2
    org = Counter(r["origin"] for r in rows if r["variant"] == "canonical")
    terms = Counter(r["canonical_term"] for r in rows if r["variant"] == "canonical")
    card = [
        "# Paraphrase-twin benchmark card (U1)",
        "",
        f"- Families: {fams} (each = 1 canonical + 1 paraphrase variant, same gold qrels)",
        f"- Origin: {dict(org)}  (paraphrase_original = the v1 query was the reworded one)",
        f"- Families per canonical term: {dict(sorted(terms.items()))}",
        f"- qrels judgments: {len(qr)} (copied from the source v1 query)",
        f"- queries_pt.csv SHA-256: `{h}`",
        "",
        "Freeze: paste the hash into experiments/configs/shared_data.yaml "
        "→ benchmarks.pt.annotations_sha256.",
        "Assumption: a lexicon swap preserves the information need. "
        "E004 is informational on this benchmark.",
    ]
    open(os.path.join(a.out, "BENCHMARK_PT_CARD.md"), "w", encoding="utf-8").write(
        "\n".join(card) + "\n"
    )
    print("\n".join(card))


if __name__ == "__main__":
    main()
