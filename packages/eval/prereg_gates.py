"""Generic preregistered-gate engine for E004–E008 (gates are data, in YAML).

Gate kinds
  gt0             cohort mean delta > 0                       (improvement gate)
  guard           cohort mean delta >= -epsilon
  equal           cohort mean delta == 0 within 1e-9          (by-construction checks)
  invariant_lists every query in cohort has identical top-k doc lists
  per_query_retain every query in cohort: treatment >= control - epsilon
Cohorts: {column: value | [values]}, 'all', or {meta: "path", equals: value}.
Each gate compares runs[treatment] against runs[control] from the YAML 'runs' map.
"""

from __future__ import annotations

from collections.abc import Callable
from statistics import mean
from typing import Any

from packages.eval.e003_comparison import CHANGE_TOL, bootstrap_ci

DEFAULT_EPS = 0.01
Record = dict[str, Any]


def _meta_get(meta: Record, path: str) -> object:
    cur = meta
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def select(cohort_def: str | Record, ann: list[Record], run: dict[str, Record]) -> list[str]:
    if cohort_def == "all":
        return [a["query_id"] for a in ann]
    if not isinstance(cohort_def, dict):
        raise ValueError(f"unknown cohort definition {cohort_def!r}")
    if "meta" in cohort_def:
        return [
            a["query_id"]
            for a in ann
            if _meta_get(run[a["query_id"]]["meta"], cohort_def["meta"]) == cohort_def["equals"]
        ]
    out = []
    for a in ann:
        if all(a.get(col) in (v if isinstance(v, list) else [v]) for col, v in cohort_def.items()):
            out.append(a["query_id"])
    return out


def evaluate(
    prereg: Record, runs: dict[str, dict[str, Record]], ann: list[Record]
) -> dict[str, Record]:
    eps = prereg.get("epsilon", DEFAULT_EPS)
    ann_by = {a["query_id"]: a for a in ann}
    cohorts = prereg["cohorts"]
    results = {}
    for g in prereg["gates"]:
        ctrl, trt = runs[g.get("control", "control")], runs[g.get("treatment", "treatment")]
        cdef = (
            cohorts[g["cohort"]]
            if isinstance(g["cohort"], str) and g["cohort"] != "all"
            else g["cohort"]
        )
        expected = set(ann_by)
        if set(ctrl) != expected or set(trt) != expected:
            raise ValueError(
                f"Gate {g['id']}: run query IDs do not match the benchmark annotations"
            )
        qids = select(cdef, ann, trt if isinstance(cdef, dict) and "meta" in cdef else ctrl)
        kind, m = g["kind"], g.get("metric", "ndcg@10")
        r: Record = {
            "id": g["id"],
            "hypothesis": g.get("hypothesis", ""),
            "cohort": g["cohort"],
            "metric": m,
            "kind": kind,
            "n": len(qids),
            "improvement_gate": kind == "gt0",
            "control": g.get("control", "control"),
            "treatment": g.get("treatment", "treatment"),
        }
        r["component"] = g.get("component")
        if len(qids) < g.get("min_n", 1):
            r.update(
                status=f"NOT EVALUABLE (n={len(qids)} < {g.get('min_n', 1)})",
                passed=False,
                not_evaluable=True,
            )
        elif kind == "invariant_lists":
            k = g.get("k", 50)
            changed = [q for q in qids if ctrl[q]["ranked"][:k] != trt[q]["ranked"][:k]]
            r.update(changed=changed[:50], n_changed=len(changed), passed=not changed)
        elif kind == "per_query_retain":
            rows = [
                {"query_id": q, "control": ctrl[q]["metrics"][m], "treatment": trt[q]["metrics"][m]}
                for q in qids
            ]
            r.update(rows=rows, passed=all(x["treatment"] >= x["control"] - eps for x in rows))
        else:
            d = [trt[q]["metrics"][m] - ctrl[q]["metrics"][m] for q in qids]
            groups: dict[str, list[float]] = {}
            for q, x in zip(qids, d, strict=True):
                groups.setdefault(ann_by[q]["query"].strip().lower(), []).append(x)
            dd = mean(mean(v) for v in groups.values())
            tests: dict[str, Callable[[float], bool]] = {
                "gt0": lambda v: v > CHANGE_TOL,
                "guard": lambda v: v >= -eps,
                "equal": lambda v: abs(v) <= CHANGE_TOL,
            }
            test = tests[kind]
            qw, ok_dd = test(mean(d)), test(dd)
            r.update(
                delta=mean(d),
                delta_dedup=dd,
                ci95=bootstrap_ci(d),
                n_unique=len(groups),
                improved=sum(x > CHANGE_TOL for x in d),
                regressed=sum(x < -CHANGE_TOL for x in d),
                passed=qw,
                fragile=qw and not ok_dd,
            )
        r.setdefault(
            "status", ("PASS (fragile)" if r.get("fragile") else "PASS") if r["passed"] else "FAIL"
        )
        results[g["id"]] = r
    return results


def verdict(gates: dict[str, Record]) -> str:
    if not gates:
        return "NOT_EVALUABLE"
    if any(g.get("not_evaluable") for g in gates.values()):
        return "NOT_EVALUABLE"
    if all(g["passed"] for g in gates.values()):
        return (
            "NOT_ADOPTED_FRAGILE"
            if any(g["improvement_gate"] and g.get("fragile") for g in gates.values())
            else "ADOPT_CANDIDATE"
        )
    if any(not g["passed"] and not g["improvement_gate"] for g in gates.values()):
        return "NOT_ADOPTED_GUARDRAIL_FAILURE"
    return "NULL_RESULT"


def component_verdicts(gates: dict[str, Record]) -> dict[str, str]:
    """Component-tagged gates decide that component; untagged gates apply to all."""
    comps = sorted({g["component"] for g in gates.values() if g.get("component")})
    out = {}
    for c in comps:
        sub = {k: g for k, g in gates.items() if g.get("component") in (None, c)}
        if any(g.get("not_evaluable") for g in sub.values() if g.get("component") == c):
            out[c] = "NOT_EVALUABLE"
        else:
            out[c] = verdict(sub)
    return out
