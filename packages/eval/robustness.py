"""U1 — paraphrase robustness for the same need worded differently.

Annotations have `family_id` and `variant` columns (built by build_paraphrase_twins.py).
Every family has one canonical and one paraphrase variant sharing the SAME gold qrels,
so any score difference is caused by wording alone.

Per-family statistics (all on the run's ranked lists and per-query metrics):
  abs_gap   |NDCG@10(canonical) - NDCG@10(paraphrase)|        lower is better
  worst     min NDCG@10 over the family's variants             higher is better
  para      NDCG@10 of the paraphrase variant                  higher is better
  overlap   Jaccard overlap of the two top-10 document sets    higher is better
"""

from __future__ import annotations

from collections.abc import Collection
from statistics import mean
from typing import Any

Record = dict[str, Any]

STATS = {"abs_gap": -1, "worst": +1, "para": +1, "overlap": +1}  # sign = direction of "better"


def families(ann: list[Record], qids: Collection[str] | None = None) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for a in ann:
        if qids is not None and a["query_id"] not in qids:
            continue
        if a.get("family_id"):
            out.setdefault(a["family_id"], {})[a["variant"]] = a["query_id"]
    return {f: v for f, v in out.items() if "canonical" in v and "paraphrase" in v}


def family_stats(
    run: dict[str, Record], fam: dict[str, str], metric: str = "ndcg@10", k: int = 10
) -> dict[str, float]:
    c, p = run[fam["canonical"]], run[fam["paraphrase"]]
    mc, mp = c["metrics"][metric], p["metrics"][metric]
    a, b = set(c["ranked"][:k]), set(p["ranked"][:k])
    return {
        "abs_gap": abs(mc - mp),
        "worst": min(mc, mp),
        "para": mp,
        "overlap": (len(a & b) / len(a | b)) if (a | b) else 1.0,
    }


def summarize(run: dict[str, Record], ann: list[Record], metric: str = "ndcg@10") -> Record:
    fams = families(ann, set(run))
    rows = {f: family_stats(run, v, metric) for f, v in fams.items()}
    if not rows:
        return {"n_families": 0}
    out: Record = {"n_families": len(rows)}
    for s in STATS:
        out[f"mean_{s}"] = mean(r[s] for r in rows.values())
    out["inconsistent_share"] = mean(r["abs_gap"] > 0.10 for r in rows.values())
    return out


def oriented_deltas(
    ctrl: dict[str, Record],
    trt: dict[str, Record],
    ann: list[Record],
    qids: Collection[str],
    stat: str,
    metric: str = "ndcg@10",
) -> dict[str, float]:
    """One value per family; positive always means 'treatment is better on this statistic'."""
    fams = families(ann, set(qids))
    sign = STATS[stat]
    return {
        f: sign * (family_stats(trt, v, metric)[stat] - family_stats(ctrl, v, metric)[stat])
        for f, v in fams.items()
    }
