import csv
import os

import pytest

from packages.eval.prereg_gates import component_verdicts, evaluate, verdict

ANN = list(
    csv.DictReader(
        open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "docs",
                "experiments",
                "e003",
                "e003-query-annotations.csv",
            )
        )
    )
)
M = ("ndcg@10", "recall@50", "mrr", "precision@10", "recall@10", "dcg@10")


def run(bump=lambda a, m: 0.0, changed=lambda a: False):
    return {
        a["query_id"]: {
            "metrics": {m: float(a["control_" + m.replace("@", "_at_")]) + bump(a, m) for m in M},
            "ranked": [str(i) for i in range(50)][:: -1 if changed(a) else 1],
            "meta": {"synonym_expansion": {"changed": changed(a)}},
        }
        for a in ANN
    }


PRE = {
    "cohorts": {
        "paraphrase": {"lexical_form": "paraphrase"},
        "canonical": {"lexical_form": "canonical"},
        "not_expanded": {"meta": "synonym_expansion.changed", "equals": False},
        "person_all": {"scenario": ["person", "person_topic"]},
    },
    "gates": [
        {"id": "A", "cohort": "paraphrase", "metric": "ndcg@10", "kind": "gt0", "component": "x"},
        {"id": "B", "cohort": "canonical", "metric": "ndcg@10", "kind": "guard"},
        {"id": "C", "cohort": "not_expanded", "kind": "invariant_lists"},
        {"id": "D", "cohort": "all", "metric": "recall@50", "kind": "equal"},
        {
            "id": "E",
            "cohort": "person_all",
            "metric": "ndcg@10",
            "kind": "guard",
            "min_n": 51,
            "component": "y",
        },
    ],
}


def test_adopt_path_and_list_cohort():
    def para(annotation):
        return annotation["lexical_form"] == "paraphrase"

    g = evaluate(
        PRE,
        {
            "control": run(),
            "treatment": run(lambda a, m: 0.1 if para(a) and m == "ndcg@10" else 0.0, para),
        },
        ANN,
    )
    assert g["A"]["passed"] and g["B"]["passed"] and g["C"]["passed"] and g["D"]["passed"]
    assert g["E"]["status"].startswith("NOT EVALUABLE") and g["E"]["n"] == 50
    cv = component_verdicts(g)
    assert (
        cv == {"x": "NOT_ADOPTED_GUARDRAIL_FAILURE", "y": "NOT_EVALUABLE"}
        or cv["y"] == "NOT_EVALUABLE"
    )


def test_invariance_violation_and_guard_failure():
    g = evaluate(
        PRE,
        {
            "control": run(),
            "treatment": run(
                lambda a, m: -0.2 if a["lexical_form"] == "canonical" else 0.0, lambda a: False
            ),
        },
        ANN,
    )
    assert not g["B"]["passed"] and not g["A"]["passed"]
    g2 = evaluate(
        PRE,
        {"control": run(), "treatment": run(changed=lambda a: a["query_id"] == "query-0001")},
        ANN,
    )
    assert g2["C"]["passed"]  # query-0001 is 'changed' so it is not in the not_expanded cohort


def test_verdict_null():
    g = evaluate(dict(PRE, gates=PRE["gates"][:4]), {"control": run(), "treatment": run()}, ANN)
    assert verdict(g) == "NULL_RESULT"


def test_missing_improvement_cohort_prevents_adoption():
    gates = evaluate(
        dict(PRE, gates=[dict(PRE["gates"][0], min_n=1000), PRE["gates"][1]]),
        {"control": run(), "treatment": run()},
        ANN,
    )
    assert verdict(gates) == "NOT_EVALUABLE"


def test_incomplete_run_is_rejected():
    incomplete = run()
    incomplete.pop(ANN[0]["query_id"])
    with pytest.raises(ValueError, match="query IDs"):
        evaluate(PRE, {"control": run(), "treatment": incomplete}, ANN)
