#!/usr/bin/env python3
"""E003 Gate 0 — corpus- and qrels-side coverage audit.

Run BEFORE any E003 treatment run. It checks that the frozen benchmark can
actually measure field-aware and temporal effects. It reads only the corpus,
the qrels and the frozen E003 query annotations; it never runs retrieval.

Usage:
  PYTHONPATH=. python scripts/audit_e003_corpus.py \
      --emails  <path to emails .json/.jsonl> \
      --qrels   <path to qrels: TREC 'qid 0 docid grade', .json {qid:{doc:grade}} or .jsonl> \
      --annotations docs/experiments/e003/e003-query-annotations.csv \
      [--field-map '{"sender":"from","timestamp":"sent_at"}'] \
      --out docs/experiments/e003/e003-gate0-corpus-audit.json

Exit code 0 = Gate 0 PASS, 1 = FAIL, 2 = input problem.
"""
import argparse, csv, json, re, sys, statistics
from collections import Counter
from datetime import datetime, timezone

from packages.search.data.e003_corpus import load_qrels

CANDIDATES = {
    "doc_id": ["doc_id", "id", "email_id", "message_id", "docid"],
    "sender": ["sender", "from", "from_name", "sender_name", "author"],
    "recipients": ["recipients", "to", "to_recipients", "recipient"],
    "cc": ["cc", "cc_recipients"],
    "subject": ["subject", "title"],
    "body": ["body", "text", "content", "body_text"],
    "attachments": ["attachment_names", "attachments", "attachment_filenames", "files"],
    "timestamp": ["timestamp", "sent_at", "date", "received_at", "datetime", "sent_date_time", "created_at"],
}
THRESHOLDS = {
    "timestamp_parse_rate": 1.0,          # every document must have a parseable time
    "sender_populated_rate": 0.99,
    "attachment_relevant_coverage": 0.90, # relevant docs of attachment queries that carry an attachment name
    "temporal_qrels_consistency": 0.80,   # temporal queries whose newest relevant doc holds the top grade
    "sender_qrels_consistency": 0.90,     # relevant docs of full-name sender queries whose sender matches
}

def load_records(path):
    with open(path, encoding="utf-8") as f:
        txt = f.read().strip()
    if not txt:
        return []
    if txt[0] == "[":
        return json.loads(txt)
    if txt[0] == "{":
        try:
            obj = json.loads(txt)
            for k in ("emails", "documents", "docs", "items", "records"):
                if isinstance(obj.get(k), list):
                    return obj[k]
            return [obj]
        except json.JSONDecodeError:
            pass
    return [json.loads(l) for l in txt.splitlines() if l.strip()]

def resolve_fields(sample, override):
    keys = set().union(*[set(d.keys()) for d in sample]) if sample else set()
    out = {}
    for f, cands in CANDIDATES.items():
        if f in override:
            out[f] = override[f]
            continue
        out[f] = next((c for c in cands if c in keys), None)
    return out

def as_text(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return " ".join(as_text(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        return " ".join(as_text(x) for x in v)
    return str(v)

def parse_ts(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        return datetime.fromtimestamp(x / 1000 if x > 1e11 else x, tz=timezone.utc)
    s = str(v).strip().replace("Z", "+00:00")
    for fn in (datetime.fromisoformat,):
        try:
            d = fn(s)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%d/%m/%Y %H:%M", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            d = datetime.strptime(s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None

def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emails", required=True)
    ap.add_argument("--qrels", required=True)
    ap.add_argument("--annotations", required=True)
    ap.add_argument("--field-map", default="{}")
    ap.add_argument("--out", default="e003-gate0-corpus-audit.json")
    a = ap.parse_args()

    docs = load_records(a.emails)
    qrels = load_qrels(a.qrels)
    with open(a.annotations, encoding="utf-8") as f:
        ann = list(csv.DictReader(f))
    if not docs or not qrels or not ann:
        print("Input problem: emails, qrels or annotations are empty.", file=sys.stderr)
        sys.exit(2)
    fm = resolve_fields(docs[:200], json.loads(a.field_map))
    if not fm["doc_id"]:
        print(f"Input problem: cannot find a document id field. Resolved: {fm}", file=sys.stderr)
        sys.exit(2)
    by_id = {str(d[fm["doc_id"]]): d for d in docs}
    get = lambda d, f: d.get(fm[f]) if fm[f] else None

    rep = {"resolved_fields": fm, "n_docs": len(docs), "n_queries_annotated": len(ann),
           "n_queries_with_qrels": sum(1 for r in ann if r["query_id"] in qrels), "thresholds": THRESHOLDS}

    # 1. Field population
    pop = {}
    for f in ("sender", "recipients", "cc", "subject", "body", "attachments", "timestamp"):
        vals = [get(d, f) for d in docs]
        nonempty = [v for v in vals if as_text(v).strip()]
        pop[f] = {"present_field": fm[f], "populated_rate": round(len(nonempty) / len(docs), 6),
                  "mean_tokens": round(statistics.mean([len(as_text(v).split()) for v in nonempty]), 2) if nonempty else 0}
    rep["field_population"] = pop
    ts = {k: parse_ts(get(d, "timestamp")) for k, d in by_id.items()}
    parsed = [t for t in ts.values() if t]
    rep["timestamp"] = {"parse_rate": round(len(parsed) / len(docs), 6),
                        "min": min(parsed).isoformat() if parsed else None,
                        "max": max(parsed).isoformat() if parsed else None,
                        "distinct_values": len(set(parsed)),
                        "duplicate_rate": round(1 - len(set(parsed)) / len(parsed), 6) if parsed else None}

    # 2. Temporal qrels consistency: newest relevant doc carries the top grade
    tq = [r for r in ann if r["temporal_explicit"] == "1" and r["query_id"] in qrels]
    detail, ok, eligible, single = [], 0, 0, 0
    for r in tq:
        rel = {d: g for d, g in qrels[r["query_id"]].items() if g > 0 and d in by_id}
        timed = [(ts[d], g, d) for d, g in rel.items() if ts.get(d)]
        if len(timed) == 0:
            continue
        if len(timed) == 1:
            single += 1
            newest_all = max((t for t in ts.values() if t), default=None)
            detail.append({"query_id": r["query_id"], "n_relevant": 1, "kind": "single_relevant"})
            continue
        eligible += 1
        top = max(g for _, g, _ in timed)
        newest = max(timed)
        graded = len({g for _, g, _ in timed}) > 1
        good = newest[1] == top
        ok += good
        # rank correlation between recency and grade (Spearman-like, ties ignored)
        order_t = [d for _, _, d in sorted(timed, reverse=True)]
        order_g = [d for _, _, d in sorted(timed, key=lambda x: (-x[1], x[2]))]
        rt = {d: i for i, d in enumerate(order_t)}; rg = {d: i for i, d in enumerate(order_g)}
        n = len(timed)
        rho = 1 - 6 * sum((rt[d] - rg[d]) ** 2 for d in rt) / (n * (n * n - 1)) if n > 1 else None
        detail.append({"query_id": r["query_id"], "n_relevant": n, "graded": graded,
                       "newest_has_top_grade": good, "recency_grade_rho": round(rho, 4) if rho is not None else None})
    rep["temporal_qrels"] = {"queries": len(tq), "multi_relevant_eligible": eligible, "single_relevant": single,
                             "newest_has_top_grade_rate": round(ok / eligible, 6) if eligible else None,
                             "graded_share": round(sum(1 for x in detail if x.get("graded")) / eligible, 6) if eligible else None,
                             "per_query": detail}

    # 3. Sender consistency for full-name sender queries
    sq = [r for r in ann if r["field_sender_cue"] == "1" and r["query_id"] in qrels]
    s_ok = s_tot = 0; s_detail = []
    for r in sq:
        m = re.search(r"\bfrom\s+(.+)$", r["query"])
        name = m.group(1).strip() if m else ""
        if len(name.split()) < 2 or "." in name:      # skip aliases / initials (E002b territory)
            continue
        rel = [d for d, g in qrels[r["query_id"]].items() if g > 0 and d in by_id]
        hit = sum(1 for d in rel if norm(name) in norm(as_text(get(by_id[d], "sender"))))
        s_ok += hit; s_tot += len(rel)
        s_detail.append({"query_id": r["query_id"], "name": name, "relevant": len(rel), "sender_match": hit})
    rep["sender_qrels"] = {"relevant_docs_checked": s_tot,
                           "sender_match_rate": round(s_ok / s_tot, 6) if s_tot else None, "per_query": s_detail}

    # 4. Attachment coverage
    aq = [r for r in ann if r["field_attachment_cue"] == "1" and r["query_id"] in qrels]
    a_ok = a_tot = a_term = 0; a_detail = []
    for r in aq:
        rel = [d for d, g in qrels[r["query_id"]].items() if g > 0 and d in by_id]
        has = [d for d in rel if as_text(get(by_id[d], "attachments")).strip()]
        term = norm(r.get("topic_term", ""))
        in_name = sum(1 for d in has if term and term in norm(as_text(get(by_id[d], "attachments"))))
        a_ok += len(has); a_tot += len(rel); a_term += in_name
        a_detail.append({"query_id": r["query_id"], "relevant": len(rel), "with_attachment": len(has), "topic_term_in_attachment_name": in_name})
    rep["attachment_qrels"] = {"relevant_docs_checked": a_tot,
                               "with_attachment_rate": round(a_ok / a_tot, 6) if a_tot else None,
                               "topic_term_in_name_rate": round(a_term / a_tot, 6) if a_tot else None,
                               "per_query": a_detail}

    # Gate 0
    g = {
        "G0-1_timestamps_parse": rep["timestamp"]["parse_rate"] >= THRESHOLDS["timestamp_parse_rate"],
        "G0-2_sender_populated": pop["sender"]["populated_rate"] >= THRESHOLDS["sender_populated_rate"],
        "G0-3_attachment_names_cover_relevant": (rep["attachment_qrels"]["with_attachment_rate"] or 0) >= THRESHOLDS["attachment_relevant_coverage"],
        "G0-4_temporal_qrels_recency_consistent": (rep["temporal_qrels"]["newest_has_top_grade_rate"] or 0) >= THRESHOLDS["temporal_qrels_consistency"],
        "G0-5_sender_qrels_consistent": (rep["sender_qrels"]["sender_match_rate"] or 0) >= THRESHOLDS["sender_qrels_consistency"],
        "G0-6_all_annotated_queries_have_qrels": rep["n_queries_with_qrels"] == len(ann),
    }
    rep["gate0"] = g
    rep["gate0_scope"] = {
        "E003-F_runnable": g["G0-2_sender_populated"] and g["G0-3_attachment_names_cover_relevant"] and g["G0-5_sender_qrels_consistent"] and g["G0-6_all_annotated_queries_have_qrels"],
        "E003-T_runnable": g["G0-1_timestamps_parse"] and g["G0-4_temporal_qrels_recency_consistent"] and g["G0-6_all_annotated_queries_have_qrels"],
    }
    rep["gate0_scope"]["E003-FT_runnable"] = rep["gate0_scope"]["E003-F_runnable"] and rep["gate0_scope"]["E003-T_runnable"]
    rep["gate0_pass"] = all(g.values())
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, default=str)
    print(json.dumps({"resolved_fields": fm, "gate0": g, "scope": rep["gate0_scope"]}, indent=2))
    sys.exit(0 if rep["gate0_pass"] else 1)

if __name__ == "__main__":
    main()
