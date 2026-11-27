#!/usr/bin/env python3
"""Benchmark v3 — cleaned and extended benchmark (the main benchmark from E009 on).

What it does
  1. v1 (gold): keeps each unique query string once (200 → 155); duplicates are listed in the card.
     Duplicates must share identical qrels; if not, they are kept and flagged.
  2. v2 (silver, E005): recipient / subject / date-range queries validated by a U3 audit.
  3. New silver scenarios generated from corpus metadata (seed 20261124):
       attachment_file  "attachment about <name>", "<spreadsheet|deck|document|pdf> about <name>"
       temporal_newest  "newest|most recent <topic> from <person>", "newest <project> <topic>"
       temporal_oldest  "earliest|oldest|first <topic> from <person>", ...
     grade 2 = the newest (or oldest) matching email, 1 = other matching emails.

Two phases, because new silver scenarios must pass the same U3 human check:
  draft:     build_benchmark_v3.py --emails E --v1-qrels Q --out data/benchmark_v3
             make_label_sheet.py --annotations data/benchmark_v3/queries_v3_draft.csv
                 --qrels data/benchmark_v3/qrels_v3_draft.jsonl --only-silver
                 --exclude-scenarios recipient subject date_range --emails E
                 --out data/benchmark_v3/label_audit
             (label by hand) ; python scripts/label_agreement.py --dir data/benchmark_v3/label_audit
  finalize:  build_benchmark_v3.py ... --finalize
                 --label-audit data/benchmark_v2/label_audit/label_audit.json
                     data/benchmark_v3/label_audit/label_audit.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
from collections import Counter, defaultdict

from packages.search.data.e003_corpus import (
    load_annotations,
    load_qrels,
    load_records,
    resolve_fields,
    timestamps_of,
    to_field_documents,
)

SEED = 20261124
V1 = "docs/experiments/e003/e003-query-annotations.csv"
PER_NEW_SCENARIO = 20
MIN_REL, MAX_REL = 1, 60
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
EXT_WORD = {
    "xlsx": "spreadsheet",
    "xls": "spreadsheet",
    "csv": "spreadsheet",
    "pptx": "deck",
    "ppt": "deck",
    "docx": "document",
    "doc": "document",
    "pdf": "pdf",
}
NEWEST_OPS, OLDEST_OPS = ["newest", "most recent"], ["earliest", "oldest", "first"]
COLS = [
    "query_id",
    "query",
    "scenario",
    "qrels_type",
    "source",
    "source_query_id",
    "dup_count",
    "lexical_form",
    "topic_term",
    "temporal_explicit",
    "temporal_operator",
    "temporal_direction",
    "field_sender_cue",
    "field_recipient_cue",
    "field_subject_cue",
    "field_attachment_cue",
    "e003_cohort",
    "e002b_diagnostic",
    "reference_time",
    "n_relevant",
]


def cues(q: str) -> dict:
    low = q.lower()
    op = next(
        (
            o
            for o in ["most recent", "latest", "newest", "recent", "earliest", "oldest", "first"]
            if re.search(r"\b" + o + r"\b", low)
        ),
        "",
    )
    return {
        "field_sender_cue": int(bool(re.search(r"\bfrom\b", low))),
        "field_recipient_cue": int(bool(re.search(r"\b(to|sent to|cc)\b", low))),
        "field_subject_cue": int(low.startswith("subject:") or "subject" in low.split()),
        "field_attachment_cue": int(
            bool(re.search(r"\b(attachment|attached|spreadsheet|deck|document|pdf|file)\b", low))
        ),
        "temporal_explicit": int(bool(op)),
        "temporal_operator": op,
        "temporal_direction": "oldest" if op in OLDEST_OPS else "newest" if op else "",
    }


def words(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def dedupe_v1(ann, qrels):
    groups = defaultdict(list)
    for a in ann:
        groups[a["query"].strip().lower()].append(a)
    keep, removed, conflicts = [], [], []
    for k, v in groups.items():
        sets = {json.dumps(sorted(qrels.get(a["query_id"], {}).items())) for a in v}
        if len(sets) > 1:
            conflicts.append(k)
            keep += [(a, 1) for a in v]
        else:
            keep.append((v[0], len(v)))
            removed += [a["query_id"] for a in v[1:]]
    keep.sort(key=lambda x: x[0]["query_id"])
    return keep, removed, conflicts


def new_silver(docs, ts, rng):
    out = []  # (scenario, text, rel)
    {d["doc_id"]: d for d in docs}

    def ranked_rel(ids, newest=True):
        ids = [i for i in ids if ts.get(i)]
        if not ids:
            return {}
        ext = (max if newest else min)(ids, key=lambda i: (ts[i], i))
        return {i: (2 if i == ext else 1) for i in ids}

    # attachment_file
    stems = Counter()
    for d in docs:
        for name in re.split(r"[;,]\s*|\s{2,}", d["attachment_names"]):
            name = name.strip()
            if "." in name:
                stem, ext = name.rsplit(".", 1)
                w = [x for x in words(stem) if not x.isdigit()]
                if 1 <= len(w) <= 4:
                    stems[(" ".join(w), ext.lower())] += 1
    cands = sorted(stems)
    rng.shuffle(cands)
    seen = set()
    for stem, ext in cands:
        if sum(s == "attachment_file" for s, _, _ in out) >= PER_NEW_SCENARIO:
            break
        typed = ext in EXT_WORD and rng.random() < 0.5
        text = f"{EXT_WORD[ext]} about {stem}" if typed else f"attachment about {stem}"
        if text in seen:
            continue
        sw = set(stem.split())
        rel = {}
        for d in docs:
            for name in re.split(r"[;,]\s*|\s{2,}", d["attachment_names"]):
                if "." in name and sw <= set(words(name.rsplit(".", 1)[0])):
                    e = name.rsplit(".", 1)[1].lower()
                    rel[d["doc_id"]] = max(
                        rel.get(d["doc_id"], 0),
                        2 if (not typed or EXT_WORD.get(e) == EXT_WORD[ext]) else 1,
                    )
        if MIN_REL <= len(rel) <= MAX_REL:
            seen.add(text)
            out.append(("attachment_file", text, rel))

    # temporal_newest / temporal_oldest
    senders = sorted({d["sender"] for d in docs if len(d["sender"].split()) >= 2})
    combos = [(t, s) for t in TOPICS for s in senders]
    rng.shuffle(combos)
    for scen, ops, newest in (
        ("temporal_newest", NEWEST_OPS, True),
        ("temporal_oldest", OLDEST_OPS, False),
    ):
        n = 0
        for t, s in combos:
            if n >= PER_NEW_SCENARIO:
                break
            ids = [
                d["doc_id"]
                for d in docs
                if d["sender"] == s
                and re.search(r"\b" + t + r"\b", (d["subject"] + " " + d["body"]).lower())
            ]
            rel = ranked_rel(ids, newest)
            if len(rel) >= 2 and len(rel) <= MAX_REL:  # >= 2 so that order matters
                out.append((scen, f"{rng.choice(ops)} {t} from {s}", rel))
                n += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emails", required=True)
    ap.add_argument("--field-map", default="{}")
    ap.add_argument("--v1-annotations", default=V1)
    ap.add_argument("--v1-qrels", required=True)
    ap.add_argument("--v2-dir", default="data/benchmark_v2")
    ap.add_argument("--out", default="data/benchmark_v3")
    ap.add_argument("--finalize", action="store_true")
    ap.add_argument("--label-audit", nargs="*", default=[])
    ap.add_argument("--allow-unvalidated", action="store_true", help="smoke tests only")
    a = ap.parse_args()
    rng = random.Random(SEED)
    recs = load_records(a.emails)
    fm = resolve_fields(recs, json.loads(a.field_map))
    docs, ts = to_field_documents(recs, fm), timestamps_of(recs, fm)
    ref = max(t for t in ts.values() if t).isoformat()
    v1q = load_qrels(a.v1_qrels)
    keep, removed, conflicts = dedupe_v1(load_annotations(a.v1_annotations), v1q)

    rows, qrels = [], []

    def add(base, rel):
        qid = f"v3-{len(rows):04d}"
        r = {c: "" for c in COLS}
        r.update(base)
        r.update(cues(r["query"]))
        r.update(query_id=qid, n_relevant=len(rel), reference_time=r.get("reference_time") or ref)
        rows.append(r)
        qrels.extend({"query_id": qid, "doc_id": d, "grade": g} for d, g in sorted(rel.items()))

    for x, n in keep:
        add(
            {
                "query": x["query"],
                "scenario": x["scenario"],
                "qrels_type": "gold",
                "source": "v1",
                "source_query_id": x["query_id"],
                "dup_count": n,
                "lexical_form": x.get("lexical_form", ""),
                "topic_term": x.get("topic_term", ""),
                "e003_cohort": x.get("e003_cohort", ""),
                "e002b_diagnostic": x.get("e002b_diagnostic", "0"),
            },
            v1q.get(x["query_id"], {}),
        )
    v2q = os.path.join(a.v2_dir, "queries_v2.csv")
    if os.path.exists(v2q):
        v2r = load_qrels(os.path.join(a.v2_dir, "qrels_v2.jsonl"))
        for x in load_annotations(v2q):
            add(
                {
                    "query": x["query"],
                    "scenario": x["scenario"],
                    "qrels_type": "silver",
                    "source": "v2",
                    "source_query_id": x["query_id"],
                    "dup_count": 1,
                    "lexical_form": "none",
                    "reference_time": x.get("reference_time", ""),
                },
                v2r.get(x["query_id"], {}),
            )
    for scen, text, rel in new_silver(docs, ts, rng):
        add(
            {
                "query": text,
                "scenario": scen,
                "qrels_type": "silver",
                "source": "v3",
                "dup_count": 1,
                "lexical_form": "none",
            },
            rel,
        )

    validated, dropped = None, {}
    if a.finalize:
        validated = set()
        for p in a.label_audit:
            validated |= set(json.load(open(p, encoding="utf-8"))["validated_scenarios"])
        if not a.allow_unvalidated:
            keepq = [r for r in rows if r["qrels_type"] == "gold" or r["scenario"] in validated]
            dropped = dict(Counter(r["scenario"] for r in rows if r not in keepq))
            ids = {r["query_id"] for r in keepq}
            rows, qrels = keepq, [q for q in qrels if q["query_id"] in ids]
    os.makedirs(a.out, exist_ok=True)
    tag = "" if a.finalize else "_draft"
    qp, rp = (
        os.path.join(a.out, f"queries_v3{tag}.csv"),
        os.path.join(a.out, f"qrels_v3{tag}.jsonl"),
    )
    with open(qp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    with open(rp, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in qrels)
    h = hashlib.sha256(open(qp, "rb").read()).hexdigest()
    sc = Counter((r["scenario"], r["qrels_type"]) for r in rows)
    cov = {
        k: sum(int(r[k]) for r in rows)
        for k in (
            "field_sender_cue",
            "field_recipient_cue",
            "field_subject_cue",
            "field_attachment_cue",
            "temporal_explicit",
        )
    }
    ops = Counter(r["temporal_operator"] for r in rows if r["temporal_operator"])
    card = [
        f"# Benchmark v3 card ({'FINAL' if a.finalize else 'DRAFT — not for gates'})",
        "",
        f"- Seed {SEED}; reference time for new silver queries {ref}",
        f"- v1 gold: {len(keep)} unique queries kept; {len(removed)} duplicate IDs removed; "
        f"conflicts kept: {len(conflicts)}",
        f"- Removed duplicate IDs: {', '.join(removed) if removed else 'none'}",
        f"- Total queries: {len(rows)}; judgments: {len(qrels)}",
        "",
        "| Scenario | Qrels | Queries |",
        "| --- | --- | --- |",
    ]
    card += [f"| {s} | {t} | {n} |" for (s, t), n in sorted(sc.items())]
    card += ["", f"- Cue coverage: {cov}", f"- Temporal operators: {dict(ops)}"]
    if a.finalize:
        card += [
            f"- Validated silver scenarios: {sorted(validated)}",
            f"- Dropped (not validated): {dropped or 'none'}",
            f"- queries_v3.csv SHA-256: `{h}`",
            "",
            "Freeze: paste the hash into experiments/configs/shared_data.yaml "
            "→ benchmarks.v3.annotations_sha256.",
        ]
    else:
        card += [
            "",
            "Next: label silver scenarios (make_label_sheet.py --only-silver), "
            "run label_agreement.py, then re-run with --finalize.",
        ]
    open(os.path.join(a.out, f"BENCHMARK_V3_CARD{tag.upper()}.md"), "w", encoding="utf-8").write(
        "\n".join(card) + "\n"
    )
    print("\n".join(card))


if __name__ == "__main__":
    main()
