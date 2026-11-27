from packages.eval import robustness as RB
from packages.eval.cost import comparable, gain_per_latency_gate, latency_gate, percentile
from packages.eval.prereg_gates import evaluate, verdict

ANN = [
    {
        "query_id": f"q{i}{v[0]}",
        "family_id": f"f{i}",
        "variant": v,
        "scenario": "topic",
        "query": f"x{i}{v}",
    }
    for i in range(40)
    for v in ("canonical", "paraphrase")
]


def run(para_ndcg, canon_ndcg=1.0, lat=10.0, same=False):
    out = {}
    for a in ANN:
        canon = a["variant"] == "canonical"
        ranked = [f"d{j}" for j in range(10)] if (canon or same) else [f"e{j}" for j in range(10)]
        out[a["query_id"]] = {
            "metrics": {"ndcg@10": canon_ndcg if canon else para_ndcg},
            "ranked": ranked,
            "latency_ms": lat,
        }
    return out


TIMING = {"machine": {"id": "m1"}}


def test_family_stats():
    s = RB.summarize(run(0.2), ANN)
    assert (
        s["n_families"] == 40
        and abs(s["mean_abs_gap"] - 0.8) < 1e-9
        and s["mean_worst"] == 0.2
        and s["mean_overlap"] == 0
    )
    assert RB.summarize(run(1.0, same=True), ANN)["inconsistent_share"] == 0


def test_levelling_down_does_not_pass_worst():
    # gap closes because canonical got worse: abs_gap improves, worst does not
    pre = {
        "cohorts": {},
        "gates": [
            {"id": "G", "cohort": "all", "kind": "family_gt0", "stat": "abs_gap", "min_n": 30},
            {"id": "W", "cohort": "all", "kind": "family_gt0", "stat": "worst", "min_n": 30},
        ],
    }
    g = evaluate(pre, {"control": run(0.2), "treatment": run(0.2, canon_ndcg=0.2)}, ANN)
    assert g["G"]["passed"] and not g["W"]["passed"]
    g = evaluate(pre, {"control": run(0.2), "treatment": run(0.6, same=True)}, ANN)
    assert g["G"]["passed"] and g["W"]["passed"] and g["G"]["n_families"] == 40


def test_family_min_n_not_evaluable():
    pre = {
        "cohorts": {},
        "gates": [
            {"id": "G", "cohort": "all", "kind": "family_gt0", "stat": "abs_gap", "min_n": 41}
        ],
    }
    assert evaluate(pre, {"control": run(0.2), "treatment": run(0.5)}, ANN)["G"]["not_evaluable"]


def test_latency_helpers():
    assert (
        percentile([1, 2, 3, 4, 5], 50) == 3
        and abs(percentile(list(range(1, 101)), 95) - 95.05) < 1e-9
    )
    c, t = [{"latency_ms": 10}] * 20, [{"latency_ms": 40}] * 20
    assert latency_gate({"stat": "p95", "max_ms": 50}, c, t)["passed"]
    assert not latency_gate({"stat": "p95", "max_ms": 50, "max_added_ms": 20}, c, t)["passed"]
    assert not latency_gate({"stat": "p95", "max_ratio": 3}, c, t)["passed"]
    assert gain_per_latency_gate({"min_gain_per_100ms": 0.01}, 0.004, c, t)[
        "passed"
    ]  # +30 ms, 0.013/100ms
    assert not gain_per_latency_gate({"min_gain_per_100ms": 0.01}, 0.002, c, t)["passed"]
    assert gain_per_latency_gate({"min_gain_per_100ms": 0.01}, 0.0, c, c)[
        "passed"
    ]  # not slower = free
    assert (
        comparable(None, TIMING)
        and comparable(TIMING, {"machine": {"id": "m2"}})
        and comparable(TIMING, TIMING) is None
    )


def test_verdict_hold_cost():
    pre = {
        "cohorts": {},
        "gates": [
            {"id": "Q", "cohort": "all", "metric": "ndcg@10", "kind": "gt0"},
            {"id": "C", "cohort": "all", "kind": "latency_budget", "stat": "p95", "max_ms": 100},
            {"id": "I", "cohort": "all", "metric": "ndcg@10", "kind": "gt0", "informational": True},
        ],
    }
    fast = evaluate(
        pre,
        {"control": run(0.2), "treatment": run(0.5, lat=50)},
        ANN,
        {"control": TIMING, "treatment": TIMING},
    )
    assert verdict(fast) == "ADOPT_CANDIDATE"
    slow = evaluate(
        pre,
        {"control": run(0.2), "treatment": run(0.5, lat=500)},
        ANN,
        {"control": TIMING, "treatment": TIMING},
    )
    assert verdict(slow) == "HOLD_COST" and slow["C"]["cost_gate"]
    unk = evaluate(
        pre,
        {"control": run(0.2), "treatment": run(0.5)},
        ANN,
        {"control": TIMING, "treatment": None},
    )
    assert verdict(unk) == "HOLD_COST_UNVERIFIED"
    # informational gate failing never changes the verdict
    pre2 = dict(
        pre,
        gates=pre["gates"][:2]
        + [{"id": "I", "cohort": "all", "metric": "ndcg@10", "kind": "gt0", "informational": True}],
    )
    r = evaluate(
        pre2,
        {"control": run(0.5), "treatment": run(0.5, canon_ndcg=1.0, lat=50)},
        ANN,
        {"control": TIMING, "treatment": TIMING},
    )
    assert not r["I"]["passed"] and verdict(r) == "NULL_RESULT"


def test_all_improvement_gates_blocked_is_not_evaluable():
    pre = {
        "cohorts": {},
        "gates": [
            {"id": "Q", "cohort": "all", "metric": "ndcg@10", "kind": "gt0", "min_n": 1000},
            {"id": "G", "cohort": "all", "metric": "ndcg@10", "kind": "guard"},
        ],
    }
    g = evaluate(pre, {"control": run(0.2), "treatment": run(0.5)}, ANN)
    assert verdict(g) == "NOT_EVALUABLE"
