#!/usr/bin/env python3
"""Run one E004–E008 arm (or its control) defined by a YAML pipeline.

python scripts/run_pipeline.py --config experiments/configs/010_e004_synonyms.yaml
Add --arm control or --arm treatment to select an arm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from statistics import median

import yaml

from packages.eval.cost import latency_summary, machine_fingerprint
from packages.eval.e003_metrics import compute_metrics, control_parity
from packages.search.data.e003_corpus import (
    load_annotations,
    load_qrels,
    load_records,
    resolve_fields,
    timestamps_of,
    to_field_documents,
)
from packages.search.pipeline.builder import Context, build_pipeline
from packages.search.retrieval import e003_wiring as W

V1_SHA = "ca0acd5db4dbed7a232f88ed664bce4cb9a5e5e6fb9cc7f26e3e29f5daff6d49"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--arm", required=True, help="control or a key under 'arms' in the config")
    ap.add_argument("--benchmark", default="v1", help="key under 'benchmarks' in the config")
    ap.add_argument("--warmup", type=int, default=5, help="Untimed warm-up queries")
    ap.add_argument("--repeats", type=int, default=3, help="Timed repeats; record their median")
    a = ap.parse_args()
    if a.warmup < 0 or a.repeats < 1:
        ap.error("--warmup must be nonnegative and --repeats must be positive")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    cfg = yaml.safe_load(Path(a.config).read_text(encoding="utf-8"))
    shared = yaml.safe_load(
        Path(cfg.get("shared", "experiments/configs/shared_data.yaml")).read_text(encoding="utf-8")
    )
    bench = (cfg.get("benchmarks") or shared["benchmarks"])[a.benchmark]
    smoke = os.environ.get("E003_SMOKE") == "1"

    expected = bench.get("annotations_sha256") or (V1_SHA if a.benchmark == "v1" else None)
    if expected and sha(bench["annotations"]) != expected:
        sys.exit(f"{bench['annotations']} hash differs from the frozen value; refusing to run.")
    if not expected and not smoke:
        sys.exit(
            f"Benchmark {a.benchmark} has no frozen annotations_sha256; "
            "freeze it first (see benchmark card)."
        )
    ann = load_annotations(bench["annotations"])
    qrels = load_qrels(bench["qrels"])
    data, ctl = shared["data"], shared["control"]
    records = load_records(data["emails"])
    fm = resolve_fields(records, data.get("field_map") or {})
    cdocs = (
        W.load_object(ctl["documents_loader"])(data["emails"])
        if ctl.get("documents_loader")
        else records
    )
    ctrl = (
        W.load_object(ctl["factory"])(cdocs)
        if ctl.get("factory")
        else W.build_retriever_instance(W.load_object(ctl["retriever"]), cdocs)
    )
    tokenize, tok_src = W.resolve_tokenizer(ctl.get("tokenizer"))
    k1, b, kb_src = W.resolve_bm25_params(ctrl, ctl.get("k1", 1.2), ctl.get("b", 0.75))
    ctx = Context(
        W.make_search_fn(ctrl),
        W.make_normalizer(ctl.get("normalizer"), retriever=ctrl),
        tokenize,
        k1,
        b,
        to_field_documents(records, fm),
        timestamps_of(records, fm),
        cache_dir=shared.get("cache_dir", "runs/cache"),
    )
    spec = {"base": "frozen_control", "stages": []} if a.arm == "control" else cfg["arms"][a.arm]
    build_start = time.perf_counter()
    pipe, base_spec = build_pipeline(
        spec, ctx, shared.get("frozen_control", "experiments/frozen/frozen_control.yaml")
    )
    for q in ann[: a.warmup]:
        pipe.search(q["query"], cfg.get("depth", 50))
    build_ms = (time.perf_counter() - build_start) * 1000

    gain = shared.get("gain_mode", "linear")
    per_query = []
    for q in ann:
        times = []
        for _ in range(a.repeats):
            t0 = time.perf_counter()
            ranked, meta = pipe.search(q["query"], cfg.get("depth", 50))
            times.append((time.perf_counter() - t0) * 1000)
        ms = median(times)
        ids = [d for d, _ in ranked]
        per_query.append(
            {
                "query_id": q["query_id"],
                "query": q["query"],
                "ranked": ids,
                "scores": [s for _, s in ranked],
                "latency_ms": ms,
                "metrics": compute_metrics(ids, qrels.get(q["query_id"], {}), gain),
                "meta": meta,
            }
        )
    parity = None
    if a.arm == "control" and a.benchmark == "v1" and base_spec.get("id") == "E002b":
        parity = control_parity(per_query, ann)
    out_dir = os.path.join(cfg.get("output_dir", f"runs/{cfg['experiment'].lower()}"), a.benchmark)
    os.makedirs(out_dir, exist_ok=True)
    out = {
        "experiment": cfg["experiment"],
        "arm": a.arm,
        "benchmark": a.benchmark,
        "pipeline": spec,
        "frozen_control": base_spec,
        "gain_mode": gain,
        "tokenizer": tok_src,
        "k1": k1,
        "b": b,
        "bm25_params_source": kb_src,
        "annotation_sha256": sha(bench["annotations"]),
        "control_parity": parity,
        "smoke": smoke,
        "timing": {
            "machine": machine_fingerprint(),
            "warmup": a.warmup,
            "repeats": a.repeats,
            "build_and_warmup_ms": build_ms,
            "summary": latency_summary(per_query),
        },
        "per_query": per_query,
    }
    path = os.path.join(out_dir, f"{a.arm}.json")
    Path(path).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(
        f"{cfg['experiment']} {a.arm} [{a.benchmark}] -> {path} (control = {base_spec.get('id')})"
    )
    if parity is not None:
        print(
            f"control parity vs frozen E002b: {'PASS' if parity['pass'] else 'FAIL'} "
            f"({parity['mismatches']} mismatches)"
        )
        if not parity["pass"] and not smoke:
            sys.exit(1)


if __name__ == "__main__":
    main()
