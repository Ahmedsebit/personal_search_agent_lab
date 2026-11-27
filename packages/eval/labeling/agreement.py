"""U3 — validate silver relevance labels against human labels before trusting them.

Agreement statistics
  kappa_binary     Cohen's kappa on relevant (grade > 0) vs not relevant
  kappa_quadratic  quadratically weighted kappa on the 0/1/2 grades
  weighted_agree   mean of 1 - |a - b| / 2 on 0/1/2 grades
  silver_precision share of silver-relevant pairs a human also judged relevant
  silver_recall    share of human-relevant pairs also silver-relevant (within the sample)

Preregistered thresholds (U3, 2026-11-27) live in THRESHOLDS and are copied into label_audit.json.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

Record = dict[str, Any]

THRESHOLDS = {
    "min_pairs_per_scenario": 30,  # LA-1
    "kappa_overall": 0.60,  # LA-2  reported only: scenarios are validated one by one
    "kappa_scenario": 0.60,  # LA-3  per scenario, binary
    "silver_precision_scenario": 0.80,  # LA-4  per scenario
    "llm_kappa_for_reuse": 0.70,  # LJ-1  informational: may the LLM judge label future benchmarks?
}


def cohen_kappa(
    a: Sequence[int],
    b: Sequence[int],
    weights: str | None = None,
    labels: Sequence[int] = (0, 1, 2),
) -> float | None:
    n = len(a)
    if n == 0:
        return None
    labels = sorted(set(labels) | set(a) | set(b))
    idx = {label: i for i, label in enumerate(labels)}
    k = len(labels)
    w = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            if weights == "quadratic":
                w[i][j] = ((i - j) ** 2) / ((k - 1) ** 2) if k > 1 else 0.0
            else:
                w[i][j] = 0.0 if i == j else 1.0
    obs = Counter(zip(a, b, strict=True))
    ca, cb = Counter(a), Counter(b)
    po = sum(w[idx[x]][idx[y]] * c for (x, y), c in obs.items()) / n
    pe = sum(w[idx[x]][idx[y]] * ca[x] * cb[y] for x in ca for y in cb) / (n * n)
    if pe == 0:
        return 1.0 if po == 0 else None
    return 1.0 - po / pe


def agreement(ref: list[int], other: list[int]) -> Record:
    rb, ob = [int(x > 0) for x in ref], [int(x > 0) for x in other]
    n = len(ref)
    sp = [h for h, s in zip(rb, ob, strict=True) if s]
    hr = [s for h, s in zip(rb, ob, strict=True) if h]
    return {
        "n": n,
        "kappa_binary": cohen_kappa(rb, ob, labels=(0, 1)),
        "kappa_quadratic": cohen_kappa(ref, other, "quadratic"),
        "weighted_agree": (sum(1 - abs(x - y) / 2 for x, y in zip(ref, other, strict=True)) / n)
        if n
        else None,
        "precision": (sum(sp) / len(sp)) if sp else None,
        "recall": (sum(hr) / len(hr)) if hr else None,
        "human_relevant_rate": (sum(rb) / n) if n else None,
    }


def audit(rows: list[Record], thresholds: Record = THRESHOLDS) -> Record:
    """Audit graded rows; ignore rows without a human grade."""
    rows = [r for r in rows if str(r.get("human_grade", "")).strip() != ""]
    for r in rows:
        r["human_grade"], r["silver_grade"] = (
            int(float(r["human_grade"])),
            int(float(r["silver_grade"])),
        )
    out: Record = {"thresholds": thresholds, "overall": {}, "scenarios": {}, "llm": {}}
    hum = [r["human_grade"] for r in rows]
    out["overall"] = agreement(hum, [r["silver_grade"] for r in rows])
    ko = out["overall"]["kappa_binary"]
    out["overall"]["LA-2"] = bool(ko is not None and ko >= thresholds["kappa_overall"])
    for sc in sorted({r["scenario"] for r in rows}):
        rs = [r for r in rows if r["scenario"] == sc]
        a = agreement([r["human_grade"] for r in rs], [r["silver_grade"] for r in rs])
        a["LA-1"] = a["n"] >= thresholds["min_pairs_per_scenario"]
        a["LA-3"] = bool(
            a["kappa_binary"] is not None and a["kappa_binary"] >= thresholds["kappa_scenario"]
        )
        a["LA-4"] = bool(
            a["precision"] is not None and a["precision"] >= thresholds["silver_precision_scenario"]
        )
        a["validated"] = a["LA-1"] and a["LA-3"] and a["LA-4"]
        a["status"] = (
            "NOT EVALUABLE (too few labelled pairs)"
            if not a["LA-1"]
            else "VALIDATED"
            if a["validated"]
            else "REJECTED"
        )
        out["scenarios"][sc] = a
    llm_rows = [r for r in rows if str(r.get("llm_grade", "")).strip() != ""]
    if llm_rows:
        a = agreement(
            [r["human_grade"] for r in llm_rows], [int(float(r["llm_grade"])) for r in llm_rows]
        )
        a["LJ-1"] = bool(
            a["kappa_binary"] is not None and a["kappa_binary"] >= thresholds["llm_kappa_for_reuse"]
        )
        out["llm"] = a
    out["validated_scenarios"] = sorted(s for s, a in out["scenarios"].items() if a["validated"])
    return out


def gate_scenarios(cohort_def: str | Record) -> list[str] | None:
    """Scenarios a gate's cohort covers; None means 'all scenarios'."""
    if cohort_def == "all" or not isinstance(cohort_def, dict) or "scenario" not in cohort_def:
        return None
    v = cohort_def["scenario"]
    return [str(s) for s in v] if isinstance(v, list) else [str(v)]


def apply_label_audit(
    gates: dict[str, Record], cohorts: Record, audit_obj: Record | None, reason_missing: str
) -> dict[str, Record]:
    """Mark gates NOT EVALUABLE when their scenarios' silver labels are not validated."""
    for g in gates.values():
        bad: str | None
        if g.get("cost_gate"):
            continue
        if audit_obj is None:
            bad = reason_missing
        else:
            cdef = (
                cohorts.get(g["cohort"], g["cohort"])
                if isinstance(g["cohort"], str)
                else g["cohort"]
            )
            scs = gate_scenarios(cdef) or list(audit_obj["scenarios"])
            failed = [s for s in scs if s not in audit_obj["validated_scenarios"]]
            bad = f"silver labels not validated for: {', '.join(failed)}" if failed else None
        if bad:
            g.update(
                status=f"NOT EVALUABLE ({bad})",
                passed=False,
                not_evaluable=True,
                label_audit_blocked=True,
            )
    return gates
