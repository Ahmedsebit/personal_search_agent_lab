import csv, os
from packages.eval import e003_comparison as C

ANN = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "experiments", "e003", "e003-query-annotations.csv")
M = ("ndcg@10", "recall@50", "mrr", "precision@10", "recall@10", "dcg@10")


def run(ann, bump=None, fired=None, change_ranked=None):
    out = {}
    for a in ann:
        base = {m: float(a["control_" + m.replace("@", "_at_")]) for m in M}
        if bump:
            base = {m: v + bump(a, m) for m, v in base.items()}
        ranked = [f"{a['query_id']}-d{i}" for i in range(50)]
        if change_ranked and change_ranked(a):
            ranked = list(reversed(ranked))
        out[a["query_id"]] = {"metrics": base, "ranked": ranked,
                              "meta": {"temporal_fired": fired(a) if fired else False}}
    return out


ANNS = list(csv.DictReader(open(ANN)))


def test_identical_arm_is_null_result_for_f():
    ctrl = run(ANNS)
    _, g = C.gates_f(ctrl, run(ANNS), ANNS)
    assert not g["F-A"]["pass"] and all(g[k]["pass"] for k in ("F-B", "F-C", "F-D", "F-E", "F-F", "F-G"))
    assert C.arm_verdict(g)["verdict"] == "NULL_RESULT"


def test_f_improvement_adopts():
    ctrl = run(ANNS)
    trt = run(ANNS, bump=lambda a, m: 0.05 if a["sub_f_ordering"] == "1" and m == "ndcg@10" else 0.0)
    _, g = C.gates_f(ctrl, trt, ANNS)
    assert g["F-A"]["status"] == "PASS" and C.arm_verdict(g)["verdict"] == "ADOPT_CANDIDATE"


def test_fragile_when_only_duplicates_improve():
    ctrl = run(ANNS)
    dup = lambda a, m: (0.2 if a["query"].lower() == "attachment about cedar move-over" and m == "ndcg@10"
                        else (-0.15 if a["query_id"] in ("query-0042", "query-0090") and m == "ndcg@10" else 0.0))
    _, g = C.gates_f(ctrl, run(ANNS, bump=dup), ANNS)
    assert g["F-A"]["status"] == "PASS (fragile)"
    assert C.arm_verdict(g)["verdict"] == "NOT_ADOPTED_FRAGILE"


def test_guardrail_failure_on_diagnostic():
    ctrl = run(ANNS)
    trt = run(ANNS, bump=lambda a, m: -0.5 if a["query_id"] == "query-0056" and m == "ndcg@10" else
              (0.05 if a["sub_f_ordering"] == "1" and m == "ndcg@10" else 0.0))
    _, g = C.gates_f(ctrl, trt, ANNS)
    assert not g["F-G"]["pass"] and C.arm_verdict(g)["verdict"] == "NOT_ADOPTED_GUARDRAIL_FAILURE"


def test_t_gates_detector_and_invariance():
    ctrl = run(ANNS)
    good = run(ANNS, fired=lambda a: a["temporal_explicit"] == "1",
               bump=lambda a, m: 0.03 if a["sub_t_ordering"] == "1" and m == "ndcg@10" else 0.0)
    _, g = C.gates_t(ctrl, good, ANNS)
    assert g["T-0"]["pass"] and g["T-A"]["pass"] and g["T-B"]["pass"]
    bad = run(ANNS, fired=lambda a: True, change_ranked=lambda a: a["query_id"] == "query-0001")
    _, g = C.gates_t(ctrl, bad, ANNS)
    assert not g["T-0"]["pass"] and g["T-A"]["non_temporal_lists_changed"] == ["query-0001"]


def test_ft_interaction_and_decision():
    ctrl = run(ANNS)
    f = run(ANNS, bump=lambda a, m: 0.05 if a["sub_f_ordering"] == "1" and m == "ndcg@10" else 0.0)
    t = run(ANNS, fired=lambda a: a["temporal_explicit"] == "1",
            bump=lambda a, m: 0.03 if a["sub_t_ordering"] == "1" and m == "ndcg@10" else 0.0)
    ft = run(ANNS, bump=lambda a, m: (0.05 if a["sub_f_ordering"] == "1" else 0.0) + (0.03 if a["sub_t_ordering"] == "1" else 0.0)
             if m == "ndcg@10" else 0.0)
    _, gf = C.gates_f(ctrl, f, ANNS)
    _, gt = C.gates_t(ctrl, t, ANNS)
    _, gft, inter = C.gates_ft(ctrl, f, t, ft, ANNS)
    assert all(v["label"] == "additive" for v in inter.values())
    d = C.final_decision(C.arm_verdict(gf), C.arm_verdict(gt), C.arm_verdict(gft))
    assert d.startswith("E003-FT becomes")
