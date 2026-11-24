#!/usr/bin/env python3
"""Run one E003 arm (control | e003_f | e003_t | e003_ft) over the frozen 200 queries.

  PYTHONPATH=. python scripts/run_e003.py --config experiments/configs/007_e003_f.yaml

Run the control arm FIRST: it checks control parity against the frozen E002b
values and fixes the metric gain mode used by every other arm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import yaml

from packages.eval.e003_metrics import compute_metrics, control_parity
from packages.search.data.e003_corpus import (
    load_annotations,
    load_qrels,
    load_records,
    resolve_fields,
    timestamps_of,
    to_field_documents,
)
from packages.search.retrieval import e003_wiring as W
from packages.search.retrieval.e003_retrievers import E003Retriever
from packages.search.retrieval.field_aware_bm25 import FieldAwareBM25

FROZEN_SHA = "ca0acd5db4dbed7a232f88ed664bce4cb9a5e5e6fb9cc7f26e3e29f5daff6d49"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_queries(retriever, annotations, qrels, depth, gain_mode):
    out = []
    for a in annotations:
        t0 = time.perf_counter()
        ranked, meta = retriever.search(a["query"], depth)
        ms = (time.perf_counter() - t0) * 1000
        ids = [d for d, _ in ranked]
        out.append(
            {
                "query_id": a["query_id"],
                "query": a["query"],
                "ranked": ids,
                "scores": [s for _, s in ranked],
                "latency_ms": ms,
                "metrics": compute_metrics(ids, qrels.get(a["query_id"], {}), gain_mode),
                "meta": meta,
            }
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--allow-annotation-change", action="store_true")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    arm, data, ctl = cfg["arm"], cfg["data"], cfg["control"]

    ann_path = data["annotations"]
    if sha256(ann_path) != FROZEN_SHA and not args.allow_annotation_change:
        sys.exit(
            f"Annotation file hash differs from the preregistered {FROZEN_SHA}. Refusing to run."
        )
    annotations = load_annotations(ann_path)
    qrels = load_qrels(data["qrels"])
    records = load_records(data["emails"])
    fm = resolve_fields(records, data.get("field_map") or {})

    control_docs = records
    if ctl.get("documents_loader"):
        control_docs = W.load_object(ctl["documents_loader"])(data["emails"])
    ctrl = (
        W.load_object(ctl["factory"])(control_docs)
        if ctl.get("factory")
        else W.build_retriever_instance(W.load_object(ctl["retriever"]), control_docs)
    )
    control_search = W.make_search_fn(ctrl)
    normalize = W.make_normalizer(ctl.get("normalizer"), retriever=ctrl)
    tokenize, tok_src = W.resolve_tokenizer(ctl.get("tokenizer"))
    k1, b, kb_src = W.resolve_bm25_params(ctrl, ctl.get("k1", 1.2), ctl.get("b", 0.75))

    p = cfg.get("params", {})
    field_index = timestamps = None
    if arm in ("e003_f", "e003_ft"):
        field_index = FieldAwareBM25(to_field_documents(records, fm), k1=k1, b=b, tokenize=tokenize)
    if arm in ("e003_t", "e003_ft"):
        timestamps = timestamps_of(records, fm)
    retriever = E003Retriever(
        arm,
        control_search=control_search,
        normalize=normalize,
        field_index=field_index,
        timestamps=timestamps,
        tokenize=tokenize,
        lam=p.get("lambda", 0.30),
        depth=p.get("depth", 50),
        routing=p.get("routing", True),
        field_weights=p.get("field_weights"),
    )

    out_dir = cfg.get("output_dir", "runs/e003")
    os.makedirs(out_dir, exist_ok=True)
    gain_mode, parity = cfg.get("gain_mode", "auto"), None
    if arm == "control":
        tried = {}
        for mode in ["linear", "exponential"] if gain_mode == "auto" else [gain_mode]:
            pq = run_queries(retriever, annotations, qrels, p.get("depth", 50), mode)
            tried[mode] = (pq, control_parity(pq, annotations))
            if tried[mode][1]["pass"]:
                break
        gain_mode = next((m for m, (_, par) in tried.items() if par["pass"]), list(tried)[0])
        per_query, parity = tried[gain_mode]
    else:
        ctrl_path = os.path.join(out_dir, "control.json")
        if gain_mode == "auto":
            if not os.path.exists(ctrl_path):
                sys.exit("Run the control arm first (it fixes the metric gain mode).")
            gain_mode = json.load(open(ctrl_path))["gain_mode"]
        per_query = run_queries(retriever, annotations, qrels, p.get("depth", 50), gain_mode)

    result = {
        "arm": arm,
        "experiment": "E003",
        "gain_mode": gain_mode,
        "control_parity": parity,
        "resolved_fields": fm,
        "tokenizer": tok_src,
        "k1": k1,
        "b": b,
        "bm25_params_source": kb_src,
        "params": p,
        "smoke": os.environ.get("E003_SMOKE") == "1",
        "annotation_sha256": sha256(ann_path),
        "per_query": per_query,
    }
    path = os.path.join(out_dir, f"{arm}.json")
    json.dump(result, open(path, "w"), indent=1, default=str)
    print(
        f"{arm}: wrote {path}; gain_mode={gain_mode}; tokenizer={tok_src}; k1={k1} b={b} ({kb_src})"
    )
    if parity is not None:
        print(
            f"control parity vs frozen E002b: {'PASS' if parity['pass'] else 'FAIL'} "
            f"({parity['mismatches']} mismatches)"
        )
        if not parity["pass"] and os.environ.get("E003_SMOKE") != "1":
            print(
                "STOP: the harness does not reproduce frozen E002b. "
                "Fix wiring before running E003 arms."
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
