#!/usr/bin/env python3
"""Run E009: answers from the frozen control's retrieval + layered judges, planted failures, gates.

# 1) retrieve with the frozen control on the chosen benchmark
python scripts/run_pipeline.py --config experiments/configs/015_e009_answers.yaml
    --arm control --benchmark v3
# 2) answers, judges, planted failures, gates
PYTHONPATH=. python scripts/run_e009.py --benchmark v3
# 3) optional human check: fill would_accept in results/answer_sheet.csv, then run step 2 again
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
from pathlib import Path

import yaml

from packages.agent.answer import ExtractiveAnswerer, LLMAnswerer
from packages.eval.e009_eval import SEED, gates, run, verdict
from packages.eval.labeling.agreement import cohen_kappa
from packages.search.data.e003_corpus import (
    load_annotations,
    load_qrels,
    load_records,
    resolve_fields,
    timestamps_of,
    to_field_documents,
)


def fmt(x):
    return "—" if x is None else (f"{x:.4f}" if isinstance(x, float) else str(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", default="docs/experiments/e009/e009-gates.yaml")
    ap.add_argument("--benchmark")
    ap.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai_compatible"],
        help="for answerer: llm only",
    )
    ap.add_argument("--out", default="docs/experiments/e009/results")
    a = ap.parse_args()
    p = yaml.safe_load(Path(a.prereg).read_text(encoding="utf-8"))
    shared = yaml.safe_load(
        Path("experiments/configs/shared_data.yaml").read_text(encoding="utf-8")
    )
    bench = a.benchmark or p["benchmark"]
    b = shared["benchmarks"][bench]
    run_path = p["retrieval_run"].format(benchmark=bench)
    rf = json.loads(Path(run_path).read_text(encoding="utf-8"))
    smoke = bool(rf.get("smoke"))
    if not smoke:
        annotation_hash = hashlib.sha256(Path(b["annotations"]).read_bytes()).hexdigest()
        expected = b.get("annotations_sha256")
        if bench == "v1":
            expected = "ca0acd5db4dbed7a232f88ed664bce4cb9a5e5e6fb9cc7f26e3e29f5daff6d49"
        if not expected or annotation_hash != expected:
            raise SystemExit("Benchmark annotations are not frozen or their hash has changed")
        if rf.get("annotation_sha256") != annotation_hash or rf.get("benchmark") != bench:
            raise SystemExit("Retrieval run does not match the selected benchmark")
        if rf.get("arm") != "control":
            raise SystemExit("E009 requires retrieval from the frozen control")
        if rf.get("control_parity") and not rf["control_parity"]["pass"]:
            raise SystemExit("Retrieval control parity failed; results invalid")
    recs = load_records(shared["data"]["emails"])
    fm = resolve_fields(recs, shared["data"].get("field_map") or {})
    docs, ts = to_field_documents(recs, fm), timestamps_of(recs, fm)
    for d in docs:
        d["date"] = ts.get(d["doc_id"]).isoformat() if ts.get(d["doc_id"]) else ""
    if p["answerer"] == "llm":
        from packages.eval.labeling.llm_judge import make_provider

        answerer = LLMAnswerer(make_provider(a.provider), k=p["k"])
    else:
        answerer = ExtractiveAnswerer(k=p["k"])
    res = run(
        load_annotations(b["annotations"]),
        {q["query_id"]: q for q in rf["per_query"]},
        load_qrels(b["qrels"]),
        docs,
        ts,
        k=p["k"],
        answerer=answerer,
    )
    G = gates(res, p)
    os.makedirs(a.out, exist_ok=True)

    # Score the optional human check after the sampled sheet is filled.
    sheet = p.get("human_sheet")
    hk = None
    if sheet and os.path.exists(sheet):
        rows = [
            r
            for r in csv.DictReader(open(sheet, encoding="utf-8"))
            if r["would_accept"].strip() in ("0", "1")
        ]
        dec = {r["query_id"]: r["decision"] for r in res["real"]}
        pairs = [
            (int(r["would_accept"]), int(dec.get(r["query_id"]) in ("ACCEPT", "REPAIRED")))
            for r in rows
            if r["query_id"] in dec
        ]
        if pairs:
            hk = cohen_kappa([x for x, _ in pairs], [y for _, y in pairs], labels=(0, 1))
        G["gates"]["J-H"] = {
            "id": "J-H",
            "hypothesis": "Judge decisions agree with a person",
            "value": hk,
            "n": len(pairs),
            "requirement": f"kappa >= {p['thresholds']['human_kappa']}",
            "kind": "quality",
            "informational": True,
            "not_evaluable": not pairs or hk is None,
            "passed": hk is not None and hk >= p["thresholds"]["human_kappa"],
            "status": "NOT EVALUABLE (sheet not filled yet)"
            if not pairs or hk is None
            else ("PASS" if hk >= p["thresholds"]["human_kappa"] else "FAIL") + " (informational)",
        }
    elif sheet:
        rng = random.Random(SEED)
        sample = rng.sample(res["real"], min(40, len(res["real"])))
        Path(sheet).parent.mkdir(parents=True, exist_ok=True)
        with open(sheet, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f, fieldnames=["query_id", "query", "answer", "would_accept", "notes"]
            )
            w.writeheader()
            qtext = {q["query_id"]: q["query"] for q in load_annotations(b["annotations"])}
            for r in sample:
                w.writerow(
                    {
                        "query_id": r["query_id"],
                        "query": qtext.get(r["query_id"], ""),
                        "answer": r["answer"],
                        "would_accept": "",
                        "notes": "",
                    }
                )

    v = verdict(G["gates"])
    md = [
        f"# E009 results — benchmark {bench}",
        "",
        ("**SMOKE RUN — NOT VALID EVIDENCE**\n" if smoke else "") + f"**Verdict:** {v}",
        "",
        "| Gate | Hypothesis | n | Value | Requirement | Result |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for g in G["gates"].values():
        md.append(
            f"| {g['id']} | {g['hypothesis']} | {g['n']} | {fmt(g['value'])} | "
            f"{g['requirement']} | **{g['status']}** |"
        )
    md += [
        "",
        "## Detection by planted failure type",
        "",
        "| Type | Planted | Caught |",
        "| --- | --- | --- |",
    ]
    md += [f"| {k} | {x['n']} | {fmt(x['detection'])} |" for k, x in G["per_type"].items()]
    md += [
        "",
        "## Single judge vs layered (share of all planted failures caught)",
        "",
        "| Judge | Caught |",
        "| --- | --- |",
    ] + [f"| {j} | {fmt(x)} |" for j, x in G["single_judge_detection"].items()]
    md += [
        f"| **Layered** | **{fmt(G['layered_detection'])}** |",
        "",
        "## Real answers (frozen control retrieval)",
        "",
        f"- Answers: {G['real_summary']['n']}; decisions: {G['real_summary']['decisions']}",
        "- Mean citation precision (gold/silver qrels): "
        f"{fmt(G['real_summary']['mean_citation_precision'])}",
        "- Answers citing at least one relevant email: "
        f"{fmt(G['real_summary']['answers_citing_a_relevant_email'])}",
    ]
    if sheet and hk is None:
        md += ["", f"Human check: fill `would_accept` (1/0) in `{sheet}` and re-run for J-H."]
    json.dump(
        {
            "verdict": v,
            "smoke": smoke,
            "benchmark": bench,
            "run": run_path,
            "answerer": answerer.name,
            **G,
            "real": res["real"],
        },
        open(os.path.join(a.out, "e009-results.json"), "w", encoding="utf-8"),
        indent=1,
        default=str,
    )
    Path(a.out, "e009-results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
