"""E003 preregistered gate evaluation (frozen 2026-11-24)."""

from __future__ import annotations

import random
from collections.abc import Callable
from statistics import mean

from packages.eval.e003_metrics import METRICS

EPS = 0.01
CHANGE_TOL = 1e-9
BOOT = {"resamples": 10000, "seed": 20261124}


def cohorts(ann: list[dict]) -> dict[str, Callable[[dict], bool]]:
    return {
        "all": lambda a: True,
        "field_only": lambda a: a["e003_cohort"] == "field_only",
        "temporal_only": lambda a: a["e003_cohort"] == "temporal_only",
        "field_and_temporal": lambda a: a["e003_cohort"] == "field_and_temporal",
        "neither": lambda a: a["e003_cohort"] == "neither",
        "attachment": lambda a: a["field_attachment_cue"] == "1",
        "person_all": lambda a: a["scenario"] in ("person", "person_topic"),
        "person": lambda a: a["scenario"] == "person",
        "temporal_all": lambda a: a["temporal_explicit"] == "1",
        "non_temporal": lambda a: a["temporal_explicit"] == "0",
        "sub_f_ordering": lambda a: a["sub_f_ordering"] == "1",
        "sub_t_ordering": lambda a: a["sub_t_ordering"] == "1",
        "sub_paraphrase_recall_limited": lambda a: a["sub_paraphrase_recall_limited"] == "1",
        "e002b_diagnostic": lambda a: a["e002b_diagnostic"] == "1",
    }


def _deltas(ctrl: dict, trt: dict, qids: list[str], metric: str) -> list[float]:
    return [trt[q]["metrics"][metric] - ctrl[q]["metrics"][metric] for q in qids]


def _dedup(ann_by: dict, qids: list[str], deltas: list[float]) -> list[float]:
    groups: dict[str, list[float]] = {}
    for q, d in zip(qids, deltas, strict=True):
        groups.setdefault(ann_by[q]["query"].strip().lower(), []).append(d)
    return [mean(v) for v in groups.values()]


def bootstrap_ci(values: list[float], resamples=BOOT["resamples"], seed=BOOT["seed"]):
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    ms = sorted(sum(rng.choices(values, k=n)) / n for _ in range(resamples))
    return [ms[int(0.025 * resamples)], ms[int(0.975 * resamples) - 1]]


def cohort_table(
    ctrl: dict, trt: dict, ann: list[dict], with_ci=("ndcg@10", "recall@50", "mrr")
) -> dict:
    ann_by = {a["query_id"]: a for a in ann}
    out = {}
    for name, pred in cohorts(ann).items():
        qids = [
            a["query_id"] for a in ann if pred(a) and a["query_id"] in ctrl and a["query_id"] in trt
        ]
        if not qids:
            continue
        row = {"n": len(qids), "n_unique": len({ann_by[q]["query"].strip().lower() for q in qids})}
        for m in METRICS:
            d = _deltas(ctrl, trt, qids, m)
            row[m] = {"delta": mean(d), "delta_dedup": mean(_dedup(ann_by, qids, d))}
            if m in with_ci:
                row[m]["ci95"] = bootstrap_ci(d)
        nd = _deltas(ctrl, trt, qids, "ndcg@10")
        row["improved"] = sum(x > CHANGE_TOL for x in nd)
        row["regressed"] = sum(x < -CHANGE_TOL for x in nd)
        row["unchanged"] = len(nd) - row["improved"] - row["regressed"]
        out[name] = row
    return out


def _gate(table, cohort, metric, kind, *, improvement=False):
    """kind: 'gt0' (strict improvement) or 'guard' (>= -EPS)."""
    r = table[cohort][metric]
    test = (lambda v: v > CHANGE_TOL) if kind == "gt0" else (lambda v: v >= -EPS)
    qw, dd = test(r["delta"]), test(r["delta_dedup"])
    status = "PASS" if qw and dd else ("PASS (fragile)" if qw else "FAIL")
    return {
        "cohort": cohort,
        "metric": metric,
        "requirement": "> 0" if kind == "gt0" else f">= -{EPS}",
        "delta": r["delta"],
        "delta_dedup": r["delta_dedup"],
        "ci95": r.get("ci95"),
        "status": status,
        "pass": qw,
        "improvement_gate": improvement,
    }


def _both(*gs):
    ok = all(g["pass"] for g in gs)
    status = (
        "FAIL"
        if not ok
        else ("PASS (fragile)" if any("fragile" in g["status"] for g in gs) else "PASS")
    )
    return {
        "parts": list(gs),
        "pass": ok,
        "status": status,
        "improvement_gate": any(g["improvement_gate"] for g in gs),
    }


def _diag_gate(ctrl, trt, ann):
    rows, ok = [], True
    for a in ann:
        if a["e002b_diagnostic"] == "1":
            c, t = (
                ctrl[a["query_id"]]["metrics"]["ndcg@10"],
                trt[a["query_id"]]["metrics"]["ndcg@10"],
            )
            good = t >= c - EPS
            ok &= good
            rows.append(
                {
                    "query_id": a["query_id"],
                    "query": a["query"],
                    "control": c,
                    "treatment": t,
                    "pass": good,
                }
            )
    return {
        "parts": rows,
        "pass": ok,
        "status": "PASS" if ok else "FAIL",
        "improvement_gate": False,
    }


def gates_f(ctrl, trt, ann):
    t = cohort_table(ctrl, trt, ann)
    return t, {
        "F-A": _gate(t, "field_only", "ndcg@10", "gt0", improvement=True),
        "F-B": _gate(t, "field_only", "recall@50", "guard"),
        "F-C": _both(
            _gate(t, "attachment", "ndcg@10", "guard"), _gate(t, "attachment", "recall@50", "guard")
        ),
        "F-D": _both(
            _gate(t, "person_all", "ndcg@10", "guard"), _gate(t, "person_all", "recall@50", "guard")
        ),
        "F-E": _both(
            _gate(t, "neither", "ndcg@10", "guard"), _gate(t, "neither", "recall@50", "guard")
        ),
        "F-F": _gate(t, "temporal_only", "ndcg@10", "guard"),
        "F-G": _diag_gate(ctrl, trt, ann),
    }


def gates_t(ctrl, trt, ann):
    t = cohort_table(ctrl, trt, ann)
    fired = {q: bool(trt[q]["meta"].get("temporal_fired")) for q in trt}
    expected = {a["query_id"]: a["temporal_explicit"] == "1" for a in ann}
    fp = [q for q, e in expected.items() if not e and fired.get(q)]
    fn = [q for q, e in expected.items() if e and not fired.get(q)]
    changed = [
        a["query_id"]
        for a in ann
        if a["temporal_explicit"] == "0"
        and ctrl[a["query_id"]]["ranked"][:50] != trt[a["query_id"]]["ranked"][:50]
    ]
    return t, {
        "T-0": {
            "pass": not fp and not fn,
            "status": "PASS" if not fp and not fn else "FAIL",
            "false_positives": fp,
            "false_negatives": fn,
            "improvement_gate": False,
        },
        "T-A": {
            "pass": not changed,
            "status": "PASS" if not changed else "FAIL",
            "non_temporal_lists_changed": changed,
            "improvement_gate": False,
        },
        "T-B": _gate(t, "temporal_only", "ndcg@10", "gt0", improvement=True),
        "T-C": _gate(t, "temporal_only", "mrr", "guard"),
        "T-D": _gate(t, "temporal_all", "recall@50", "guard"),
        "T-E": _gate(t, "field_and_temporal", "ndcg@10", "guard"),
    }


def gates_ft(ctrl, f, tt, ft, ann):
    t = cohort_table(ctrl, ft, ann)

    def arm_vs(arm, cohort):
        qids = [a["query_id"] for a in ann if cohorts(ann)[cohort](a)]
        return mean(ft[q]["metrics"]["ndcg@10"] for q in qids), mean(
            arm[q]["metrics"]["ndcg@10"] for q in qids
        )

    fb1, fb2 = arm_vs(f, "field_only"), arm_vs(tt, "temporal_only")
    fb = {
        "field_only_FT_vs_F": fb1,
        "temporal_only_FT_vs_T": fb2,
        "pass": fb1[0] >= fb1[1] - EPS and fb2[0] >= fb2[1] - EPS,
        "improvement_gate": False,
    }
    fb["status"] = "PASS" if fb["pass"] else "FAIL"
    interaction = {}
    tf, tt_, tft = (
        cohort_table(ctrl, f, ann, ()),
        cohort_table(ctrl, tt, ann, ()),
        cohort_table(ctrl, ft, ann, ()),
    )
    for c in tft:
        i = tft[c]["ndcg@10"]["delta"] - (tf[c]["ndcg@10"]["delta"] + tt_[c]["ndcg@10"]["delta"])
        interaction[c] = {
            "I": i,
            "label": "synergy" if i > EPS else ("interference" if i < -EPS else "additive"),
        }
    return (
        t,
        {
            "FT-A": _gate(t, "all", "ndcg@10", "gt0", improvement=True),
            "FT-B": fb,
            "FT-C": _both(
                _gate(t, "field_and_temporal", "ndcg@10", "guard"),
                _gate(t, "field_and_temporal", "recall@50", "guard"),
            ),
            "FT-D": _both(
                _gate(t, "neither", "ndcg@10", "guard"), _gate(t, "neither", "recall@50", "guard")
            ),
            "FT-E": _diag_gate(ctrl, ft, ann),
        },
        interaction,
    )


def arm_verdict(gates: dict) -> dict:
    all_pass = all(g["pass"] for g in gates.values())
    fragile_improvement = any(
        g.get("improvement_gate") and "fragile" in g["status"] for g in gates.values()
    )
    guard_fail = any(not g["pass"] and not g.get("improvement_gate") for g in gates.values())
    if all_pass and not fragile_improvement:
        v = "ADOPT_CANDIDATE"
    elif all_pass:
        v = "NOT_ADOPTED_FRAGILE"
    elif guard_fail:
        v = "NOT_ADOPTED_GUARDRAIL_FAILURE"
    else:
        v = "NULL_RESULT"
    return {"all_gates_pass": all_pass, "verdict": v}


def final_decision(vf, vt, vft) -> str:
    f_ok, t_ok, ft_ok = (v["verdict"] == "ADOPT_CANDIDATE" for v in (vf, vt, vft))
    if ft_ok and f_ok and t_ok:
        return "E003-FT becomes the new frozen control (E003 final)"
    if f_ok and not t_ok:
        return (
            "Freeze E003-F as control; record E003-FT as exploratory"
            if vft["all_gates_pass"]
            else "Freeze E003-F as control"
        )
    if t_ok and not f_ok:
        return (
            "Freeze E003-T as control; record E003-FT as exploratory"
            if vft["all_gates_pass"]
            else "Freeze E003-T as control"
        )
    if f_ok and t_ok:
        return (
            "F and T adopted individually but FT failed: keep E002b control; "
            "analyse interference before any follow-up ID"
        )
    return "No arm adopted: E002b remains the frozen control"
