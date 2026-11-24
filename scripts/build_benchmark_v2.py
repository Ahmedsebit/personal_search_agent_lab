#!/usr/bin/env python3
"""E005 benchmark extension (v2): recipient, subject and date-range queries with SILVER qrels.

Queries and judgments are generated deterministically from corpus metadata (seed 20261124),
so they test whether retrieval honours structure, not human relevance. Run once, then freeze:
Freeze the printed SHA-256 in shared_data.yaml under benchmarks.v2.annotations_sha256.

  PYTHONPATH=. python scripts/build_benchmark_v2.py --emails <emails> --out data/benchmark_v2
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
from collections import Counter

from packages.search.data.e003_corpus import (
    load_records,
    resolve_fields,
    timestamps_of,
    to_field_documents,
)
from packages.search.temporal.ranges import parse_range

SEED = 20261124
PER_SCENARIO = 25
TOPICS = [
    "incident",
    "latency",
    "deployment",
    "authentication",
    "evaluation",
    "budget",
    "ranking",
    "migration",
    "design",
    "privacy",
]
RANGE_TEMPLATES = [
    "{t} from last week",
    "{t} yesterday",
    "{t} last month",
    "emails about {t} this month",
    "{t} in {month}",
]
MIN_REL, MAX_REL = 1, 60


def norm(s):
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


def split_people(text):
    return [p.strip() for p in re.split(r"[;,]|\s{2,}", text) if p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emails", required=True)
    ap.add_argument("--out", default="data/benchmark_v2")
    ap.add_argument("--field-map", default="{}")
    a = ap.parse_args()
    rng = random.Random(SEED)
    recs = load_records(a.emails)
    fm = resolve_fields(recs, json.loads(a.field_map))
    docs = to_field_documents(recs, fm)
    ts = timestamps_of(recs, fm)
    ref = max(t for t in ts.values() if t)
    queries, qrels, rejected = [], [], Counter()

    def add(scenario, text, rel, extra=None):
        if not (MIN_REL <= len(rel) <= MAX_REL):
            rejected[scenario] += 1
            return False
        qid = f"v2-{len(queries):04d}"
        row = {
            "query_id": qid,
            "query": text,
            "scenario": scenario,
            "reference_time": ref.isoformat(),
            "cue_recipient": int(scenario == "recipient"),
            "cue_subject": int(scenario == "subject"),
            "cue_date_range": int(scenario == "date_range"),
            "n_relevant": len(rel),
            "qrels_type": "silver",
        }
        row.update(extra or {})
        queries.append(row)
        qrels.extend({"query_id": qid, "doc_id": d, "grade": g} for d, g in sorted(rel.items()))
        return True

    # Recipients: exclude near-universal recipients (the mailbox owner)
    rc = Counter(p for d in docs for p in set(split_people(d["recipients"])))
    cands = [p for p, c in rc.items() if c <= 0.5 * len(docs) and len(p.split()) >= 2]
    rng.shuffle(cands)
    for p in cands:
        if sum(q["scenario"] == "recipient" for q in queries) >= PER_SCENARIO:
            break
        rel = {d["doc_id"]: 1 for d in docs if p in split_people(d["recipients"])}
        add("recipient", f"emails to {p}", rel, {"operator": "", "target": p})

    # Subjects: exact subject = grade 2, all subject words present = grade 1
    subs = sorted({d["subject"] for d in docs if len(norm(d["subject"]).split()) >= 2})
    rng.shuffle(subs)
    for s in subs:
        if sum(q["scenario"] == "subject" for q in queries) >= PER_SCENARIO:
            break
        words = set(norm(s).split())
        rel = {}
        for d in docs:
            ds = norm(d["subject"])
            if ds == norm(s):
                rel[d["doc_id"]] = 2
            elif words <= set(ds.split()):
                rel[d["doc_id"]] = 1
        add("subject", f"subject: {s}", rel, {"operator": "", "target": s})

    # Date ranges: in range AND topic term in subject/body
    months = sorted({t.strftime("%B") for t in ts.values() if t})
    combos = [(tpl, t) for tpl in RANGE_TEMPLATES for t in TOPICS]
    rng.shuffle(combos)
    for tpl, t in combos:
        if sum(q["scenario"] == "date_range" for q in queries) >= PER_SCENARIO:
            break
        text = tpl.format(t=t, month=rng.choice(months) if months else "January")
        _, r, op = parse_range(text, ref)
        if r is None:
            continue
        rel = {
            d["doc_id"]: 1
            for d in docs
            if ts.get(d["doc_id"])
            and r[0] <= ts[d["doc_id"]] < r[1]
            and re.search(r"\b" + t + r"\b", (d["subject"] + " " + d["body"]).lower())
        }
        add("date_range", text, rel, {"operator": op, "target": t})

    os.makedirs(a.out, exist_ok=True)
    qpath, rpath = os.path.join(a.out, "queries_v2.csv"), os.path.join(a.out, "qrels_v2.jsonl")
    cols = [
        "query_id",
        "query",
        "scenario",
        "reference_time",
        "cue_recipient",
        "cue_subject",
        "cue_date_range",
        "operator",
        "target",
        "n_relevant",
        "qrels_type",
    ]
    with open(qpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(queries)
    with open(rpath, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in qrels)
    h = hashlib.sha256(open(qpath, "rb").read()).hexdigest()
    counts = Counter(q["scenario"] for q in queries)
    card = [
        "# Benchmark v2 card (E005)",
        "",
        f"- Generated deterministically, seed {SEED}; reference time {ref.isoformat()}",
        f"- Queries: {len(queries)} " + str(dict(counts)),
        f"- Rejected (relevant set outside {MIN_REL}–{MAX_REL}): {dict(rejected)}",
        f"- qrels: SILVER (derived from metadata), {len(qrels)} judgments",
        f"- queries_v2.csv SHA-256: `{h}`",
        "",
        "Freeze: paste the hash into experiments/configs/shared_data.yaml "
        "under benchmarks.v2.annotations_sha256.",
        "Minimum for E005 gates: 15 queries per scenario. Fewer = that scenario is NOT EVALUABLE.",
    ]
    with open(os.path.join(a.out, "BENCHMARK_V2_CARD.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(card) + "\n")
    print("\n".join(card))


if __name__ == "__main__":
    main()
