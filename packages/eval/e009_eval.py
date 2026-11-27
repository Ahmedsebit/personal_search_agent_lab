"""E009: planted failures, false alarms, single vs layered judges, and real answers."""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from datetime import datetime
from statistics import mean
from typing import Any

from packages.agent.answer import Answer, Answerer, ExtractiveAnswerer, reference_answer
from packages.agent.judges import COUNTERPART, FROM, NEWEST, OLDEST, Judges, _norm
from packages.agent.plant import TYPES, plant
from packages.eval.cost import latency_summary

SEED = 20261124
JUDGE_IDS = ["S1", "S2", "S3", "G1", "U1", "U2", "U3"]
Record = dict[str, Any]


def _ctx(
    q: str,
    ranked_ids: Sequence[str],
    docs_by_id: dict[str, dict[str, str]],
    ts: dict[str, datetime | None],
    rel: dict[str, float],
    judges: Judges,
    k: int,
) -> Record:
    retrieved = [docs_by_id[d] for d in ranked_ids[:k] if d in docs_by_id]
    direction = "oldest" if OLDEST.search(q) else "newest" if NEWEST.search(q) else None
    m = FROM.search(q)
    tw = judges._topic_words(q)
    joined = " ".join(tw)
    tw = tw + [
        w for src, dst in COUNTERPART.items() if src in joined for w in dst.split()
    ]  # same synonyms U1 accepts
    return {
        "query": q,
        "retrieved": retrieved,
        "docs_by_id": docs_by_id,
        "ts": ts,
        "relevant": rel,
        "direction": direction,
        "person": _norm(m.group(1)) if m else None,
        "topic_words": tw,
    }


def citation_quality(ans: Answer, rel: dict[str, float]) -> dict[str, float]:
    cites = list(dict.fromkeys(c for s in ans["sentences"] for c in s["citations"]))
    if not cites:
        return {"citation_precision": 0.0, "has_relevant": 0}
    good = [c for c in cites if rel.get(c, 0) > 0]
    return {"citation_precision": len(good) / len(cites), "has_relevant": int(bool(good))}


def run(
    queries: list[Record],
    run_by_q: dict[str, Record],
    qrels: dict[str, dict[str, float]],
    docs: list[dict[str, str]],
    ts: dict[str, datetime | None],
    k: int = 5,
    answerer: Answerer | None = None,
    seed: int = SEED,
    timer: Callable[[], float] | None = None,
) -> dict[str, list[Record]]:
    import time

    timer = timer or time.perf_counter
    if set(run_by_q) != {q["query_id"] for q in queries}:
        raise ValueError("Retrieval run query IDs do not match the benchmark annotations")
    rng = random.Random(seed)
    docs_by_id = {d["doc_id"]: d for d in docs}
    people = {d["sender"] for d in docs} | {
        p.strip() for d in docs for p in d["recipients"].split(";")
    }
    J = Judges(people, ts)
    answerer = answerer or ExtractiveAnswerer(k=k)
    real, clean, planted = [], [], []
    all_ids = sorted(docs_by_id)
    for q in queries:
        qid, text = q["query_id"], q["query"]
        rel = qrels.get(qid, {})
        ranked = run_by_q[qid]["ranked"]
        ctx = _ctx(text, ranked, docs_by_id, ts, rel, J, k)
        # 1) real answer from the frozen control's retrieval
        if ctx["retrieved"]:
            ans = answerer.answer(text, ctx["retrieved"])
            t0 = timer()
            dec = J.decide(text, ans, ctx["retrieved"], docs_by_id)
            ms = (timer() - t0) * 1000
            real.append(
                dict(
                    query_id=qid,
                    scenario=q.get("scenario", ""),
                    decision=dec["decision"],
                    latency_ms=ms,
                    answer=ans["text"],
                    **citation_quality(ans, rel),
                )
            )
        # Judge clean references against their gold sources plus the retrieved top-k.
        ref = reference_answer(text, rel, docs_by_id, ts, newest_first=ctx["direction"] != "oldest")
        if not ref["sentences"]:
            continue
        used = [docs_by_id[c] for s in ref["sentences"] for c in s["citations"]]
        pool = list({d["doc_id"]: d for d in used + ctx["retrieved"]}.values())
        pool_ids = {d["doc_id"] for d in pool}
        pctx = dict(
            ctx,
            retrieved=pool,
            outside=[
                docs_by_id[i]
                for i in rng.sample(all_ids, min(200, len(all_ids)))
                if i not in pool_ids
            ],
        )
        res = J.run_all(text, ref, pool, docs_by_id)
        dec = J.decide(text, ref, pool, docs_by_id)
        clean.append(
            {
                "query_id": qid,
                "decision": dec["decision"],
                "judges": {j: res[j]["passed"] for j in JUDGE_IDS},
            }
        )
        # 3) planted failures
        for kind in TYPES:
            bad = plant(kind, ref, pctx, rng)
            if bad is None:
                continue
            res = J.run_all(text, bad, pool, docs_by_id)
            dec = J.decide(text, bad, pool, docs_by_id)
            planted.append(
                {
                    "query_id": qid,
                    "type": kind,
                    "expected_layer": TYPES[kind],
                    "decision": dec["decision"],
                    "stopped_at": dec.get("stopped_at"),
                    "judges": {j: res[j]["passed"] for j in JUDGE_IDS},
                }
            )
    return {"real": real, "clean": clean, "planted": planted}


def rate(xs: Sequence[float]) -> float | None:
    return (sum(xs) / len(xs)) if xs else None


def gates(res: dict[str, list[Record]], prereg: Record) -> Record:
    th = prereg["thresholds"]
    P, C, R = res["planted"], res["clean"], res["real"]

    def caught(p: Record) -> bool:
        return bool(p["decision"] != "ACCEPT")

    out: dict[str, Record] = {}

    def g(
        gid: str,
        hyp: str,
        value: float | None,
        req: str,
        ok: bool,
        n: int,
        min_n: int = 1,
        kind: str = "quality",
        info: bool = False,
    ) -> None:
        ne = n < min_n
        out[gid] = {
            "id": gid,
            "hypothesis": hyp,
            "value": value,
            "requirement": req,
            "n": n,
            "kind": kind,
            "informational": info,
            "not_evaluable": ne,
            "passed": (not ne) and bool(ok),
            "status": f"NOT EVALUABLE (n={n} < {min_n})"
            if ne
            else ("PASS" if ok else "FAIL") + (" (informational)" if info else ""),
        }

    saf = [p for p in P if p["expected_layer"] == "safety"]
    v = rate([caught(p) for p in saf])
    g(
        "J-A",
        "Layered judges catch planted safety failures",
        v,
        f">= {th['safety_recall']}",
        v is not None and v >= th["safety_recall"],
        len(saf),
        th["min_planted"],
    )
    fa_s = rate([not all(c["judges"][j] for j in ("S1", "S2", "S3")) for c in C])
    g(
        "J-B1",
        "Few false safety alarms on clean answers",
        fa_s,
        f"<= {th['safety_false_alarm']}",
        fa_s is not None and fa_s <= th["safety_false_alarm"],
        len(C),
        th["min_clean"],
    )
    fa = rate([c["decision"] not in ("ACCEPT",) for c in C])
    g(
        "J-B2",
        "Few clean answers held back for any reason",
        fa,
        f"<= {th['any_false_alarm']}",
        fa is not None and fa <= th["any_false_alarm"],
        len(C),
        th["min_clean"],
    )
    layered = rate([caught(p) for p in P])
    singles = {j: rate([not p["judges"][j] for p in P]) for j in JUDGE_IDS}
    best_j = max(singles, key=lambda j: singles[j] or 0) if P else None
    best_rate = singles.get(best_j) if best_j is not None else None
    g(
        "J-C",
        f"Layered beats the best single judge ({best_j})",
        layered - best_rate if layered is not None and best_rate is not None else None,
        "> 0",
        layered is not None and best_rate is not None and layered - best_rate > 1e-9,
        len(P),
        th["min_planted"],
    )
    per: dict[str, Record] = {}
    for kind in TYPES:
        xs = [caught(p) for p in P if p["type"] == kind]
        per[kind] = {"n": len(xs), "detection": rate(xs)}
    evaluable = {k: v for k, v in per.items() if v["n"] >= th["min_per_type"]}
    worst = min((v["detection"] for v in evaluable.values()), default=None)
    g(
        "J-D",
        "Every planted failure type is caught often enough",
        worst,
        f"each >= {th['per_type_recall']} (types with n >= {th['min_per_type']})",
        worst is not None and worst >= th["per_type_recall"],
        len(evaluable),
        3,
    )
    acc = [r["citation_precision"] for r in R if r["decision"] in ("ACCEPT", "REPAIRED")]
    rej = [r["citation_precision"] for r in R if r["decision"] not in ("ACCEPT", "REPAIRED")]
    diff = (mean(acc) - mean(rej)) if acc and rej else None
    g(
        "J-E",
        "Accepted real answers cite relevant emails more often than held-back ones",
        diff,
        "> 0",
        diff is not None and diff > 1e-9,
        min(len(acc), len(rej)),
        th["min_real_each"],
    )
    lat = latency_summary(R)
    g(
        "J-F",
        "Judging is fast enough to run on every answer",
        lat["p95"],
        f"p95 <= {th['judge_p95_ms']} ms",
        lat["p95"] is not None and lat["p95"] <= th["judge_p95_ms"],
        lat["n"],
        1,
        kind="cost",
    )
    return {
        "gates": out,
        "per_type": per,
        "single_judge_detection": singles,
        "layered_detection": layered,
        "real_summary": {
            "n": len(R),
            "decisions": {
                d: sum(r["decision"] == d for r in R)
                for d in ("ACCEPT", "REPAIRED", "REVISE", "REJECT")
            },
            "mean_citation_precision": rate([r["citation_precision"] for r in R]),
            "answers_citing_a_relevant_email": rate([r["has_relevant"] for r in R]),
        },
    }


def verdict(gs: dict[str, Record]) -> str:
    q = {k: v for k, v in gs.items() if not v["informational"] and v["kind"] == "quality"}
    if any(v["not_evaluable"] for v in q.values()):
        return "NOT_EVALUABLE"
    if not all(v["passed"] for v in q.values()):
        return "JUDGES_NOT_VALIDATED"
    c = [v for v in gs.values() if v["kind"] == "cost"]
    if any(not v["passed"] for v in c):
        return "HOLD_COST"
    return "JUDGES_VALIDATED"
