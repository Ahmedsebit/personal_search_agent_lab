import csv, os
from packages.search.query.temporal_intent import detect_temporal_intent

ANN = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "experiments", "e003", "e003-query-annotations.csv")


def test_latest_detected_and_stripped():
    t = detect_temporal_intent("latest Atlas ranking")
    assert t.fired and t.operators == ("latest",) and t.stripped_query == "Atlas ranking"


def test_most_recent_is_one_operator():
    t = detect_temporal_intent("most recent update on Cedar")
    assert t.operators == ("most recent",) and t.stripped_query == "update on Cedar"


def test_out_of_scope_expressions_not_detected():
    for q in ("emails from last week", "yesterday Atlas", "today", "budget 2026-11-01"):
        assert not detect_temporal_intent(q).fired


def test_no_substring_false_positive():
    assert not detect_temporal_intent("latestness of recentralization").fired


def test_gate_T0_exact_on_benchmark():
    rows = list(csv.DictReader(open(ANN)))
    fired = {r["query_id"] for r in rows if detect_temporal_intent(r["query"]).fired}
    expected = {r["query_id"] for r in rows if r["temporal_explicit"] == "1"}
    assert fired == expected and len(expected) == 50
