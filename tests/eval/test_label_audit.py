from packages.eval.labeling.agreement import apply_label_audit, audit, cohen_kappa
from packages.eval.labeling.llm_judge import MockProvider, SharedAnalysisJudge


def test_kappa_known_values():
    assert cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0], labels=(0, 1)) == 1.0
    assert abs(cohen_kappa([1, 1, 0, 0], [1, 0, 1, 0], labels=(0, 1))) < 1e-12
    # po = 0.70, pe = 0.7*0.6 + 0.3*0.4 = 0.54 -> kappa = 0.16 / 0.46
    a = [1] * 25 + [1] * 10 + [0] * 5 + [0] * 10
    b = [1] * 25 + [0] * 10 + [1] * 5 + [0] * 10
    assert abs(cohen_kappa(a, b, labels=(0, 1)) - 0.16 / 0.46) < 1e-9
    assert cohen_kappa([0, 1, 2], [0, 1, 2], "quadratic") == 1.0


def rows(sc, n, flip_every=0, silver_pos_but_human_neg=0):
    out = []
    for i in range(n):
        h = i % 2
        s = h
        if flip_every and i % flip_every == 0:
            s = 1 - h
        out.append({"scenario": sc, "human_grade": str(h), "silver_grade": s, "llm_grade": h})
    for _ in range(silver_pos_but_human_neg):
        out.append({"scenario": sc, "human_grade": "0", "silver_grade": 1, "llm_grade": 0})
    return out


def test_audit_validates_and_rejects():
    r = audit(
        rows("recipient", 40)
        + rows("subject", 40, silver_pos_but_human_neg=10)
        + rows("date_range", 10)
        + [{"scenario": "recipient", "human_grade": "", "silver_grade": 1}]
    )
    assert (
        r["scenarios"]["recipient"]["status"] == "VALIDATED"
        and r["scenarios"]["recipient"]["n"] == 40
    )
    assert r["scenarios"]["subject"]["status"] == "REJECTED"  # silver precision 20/30 < 0.8
    assert r["scenarios"]["date_range"]["status"].startswith("NOT EVALUABLE")
    assert r["validated_scenarios"] == ["recipient"] and r["llm"]["LJ-1"]


def test_apply_label_audit():
    gates = {
        "A": {"cohort": "recipient"},
        "B": {"cohort": "subject"},
        "C": {"cohort": "all"},
        "D": {"cohort": "all", "cost_gate": True},
    }
    cohorts = {"recipient": {"scenario": "recipient"}, "subject": {"scenario": "subject"}}
    obj = {"scenarios": {"recipient": {}, "subject": {}}, "validated_scenarios": ["recipient"]}
    apply_label_audit(gates, cohorts, obj, "missing")
    assert (
        "not_evaluable" not in gates["A"]
        and gates["B"]["not_evaluable"]
        and gates["C"]["not_evaluable"]
    )
    assert "not_evaluable" not in gates["D"]
    g2 = {"A": {"cohort": "recipient"}}
    apply_label_audit(g2, cohorts, None, "no label audit")
    assert g2["A"]["not_evaluable"] and "no label audit" in g2["A"]["status"]


def test_shared_analysis_judge_caches_and_saves_tokens():
    j = SharedAnalysisJudge(MockProvider())
    doc = {
        "doc_id": "d1",
        "sender": "Lina Chen",
        "recipients": "Sam Reed",
        "subject": "Budget review",
        "attachment_names": "",
        "body": "Budget numbers for the quarterly review. " * 40,
    }
    for q in ("budget review", "budget from Lina Chen", "incident report", "quarterly numbers"):
        r = j.judge(q, doc)
        assert r["grade"] in (0, 1, 2)
    c = j.cost_report()
    assert c["analyse_calls"] == 1 and c["judge_calls"] == 4 and c["saving_vs_baseline_est"] > 0
    assert (
        j.judge("budget review", doc)["grade"] == 2
        and j.judge("incident report", doc)["grade"] == 0
    )


def test_bad_scenario_does_not_block_good_one():
    r = audit(rows("date_range", 60) + rows("subject", 60, flip_every=2))
    assert r["scenarios"]["date_range"]["validated"] and not r["scenarios"]["subject"]["validated"]
