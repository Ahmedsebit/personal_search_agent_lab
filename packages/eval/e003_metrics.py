"""Ranking metrics for the E003 harness.

The official numbers must match the frozen metric code. scripts/run_e003.py
therefore checks CONTROL PARITY: its control metrics must reproduce the frozen
E002b per-query values stored in e003-query-annotations.csv. The gain mode
(linear grade vs 2^grade - 1) is selected by that parity check.
"""
from __future__ import annotations

import math
from typing import Dict, List, Mapping, Sequence

METRICS = ("ndcg@10", "recall@50", "mrr", "precision@10", "recall@10", "dcg@10")


def _gain(g: float, mode: str) -> float:
    return (2.0 ** g - 1.0) if mode == "exponential" else g


def dcg(grades: Sequence[float], k: int, mode: str) -> float:
    return sum(_gain(g, mode) / math.log2(i + 2) for i, g in enumerate(grades[:k]))


def compute_metrics(ranked: Sequence[str], qrels: Mapping[str, float], gain_mode: str = "linear") -> Dict[str, float]:
    rel = {d: g for d, g in qrels.items() if g > 0}
    n_rel = len(rel)
    grades = [rel.get(d, 0.0) for d in ranked]
    ideal = sorted(rel.values(), reverse=True)
    d10 = dcg(grades, 10, gain_mode)
    idcg = dcg(ideal, 10, gain_mode)
    hits = lambda k: sum(1 for d in ranked[:k] if d in rel)
    rr = next((1.0 / (i + 1) for i, d in enumerate(ranked) if d in rel), 0.0)
    return {
        "ndcg@10": d10 / idcg if idcg > 0 else 0.0,
        "dcg@10": d10,
        "recall@50": hits(50) / n_rel if n_rel else 0.0,
        "recall@10": hits(10) / n_rel if n_rel else 0.0,
        "precision@10": hits(10) / 10.0,
        "mrr": rr,
    }


def control_parity(per_query: List[dict], annotations: List[dict], tol: float = 1e-6) -> dict:
    """Compare harness control metrics with frozen E002b values in the annotation file."""
    ann = {a["query_id"]: a for a in annotations}
    mismatches = []
    for q in per_query:
        a = ann.get(q["query_id"])
        if not a:
            continue
        for m in METRICS:
            ref = float(a["control_" + m.replace("@", "_at_")])
            if abs(q["metrics"][m] - ref) > tol:
                mismatches.append({"query_id": q["query_id"], "metric": m, "harness": q["metrics"][m], "frozen": ref})
    return {"checked_queries": len(per_query), "mismatches": len(mismatches),
            "pass": not mismatches, "examples": mismatches[:20]}
