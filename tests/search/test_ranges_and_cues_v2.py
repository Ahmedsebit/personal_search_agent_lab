from datetime import UTC, datetime

from packages.search.query.field_cues_v2 import (
    RECIPIENT_SPAN_WEIGHTS,
    SUBJECT_SPAN_WEIGHTS,
    build_query_plan_v2,
)
from packages.search.temporal.ranges import parse_range

REF = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)  # a Tuesday


def d(y, m, day):
    return datetime(y, m, day, tzinfo=UTC)


def test_relative_ranges():
    assert parse_range("budget yesterday", REF)[1] == (d(2026, 11, 23), d(2026, 11, 24))
    assert parse_range("budget from last week", REF)[1] == (d(2026, 11, 16), d(2026, 11, 23))
    assert parse_range("budget last month", REF)[1] == (d(2026, 10, 1), d(2026, 11, 1))
    q, r, op = parse_range("emails about latency in March", REF)
    assert r == (d(2026, 3, 1), d(2026, 4, 1)) and q == "emails about latency" and op == "in_month"
    assert parse_range("x in december", REF)[1][0] == d(2025, 12, 1)


def test_year_boundary_last_month():
    assert parse_range("last month", d(2026, 1, 15))[1] == (d(2025, 12, 1), d(2026, 1, 1))


def test_no_range_on_v1_queries():
    for q in ("latest Atlas ranking", "emails from Hana Okafor", "messages about rollout"):
        assert parse_range(q, REF)[1] is None


def test_recipient_and_subject_plans():
    p = build_query_plan_v2("emails to Grace Lee")
    assert p.cues[-1] == "recipient" and all(w == RECIPIENT_SPAN_WEIGHTS for _, w in p.terms)
    p = build_query_plan_v2("subject: Atlas ranking review")
    assert [t for t, _ in p.terms] == ["atlas", "ranking", "review"] and all(
        w == SUBJECT_SPAN_WEIGHTS for _, w in p.terms
    )


def test_v1_queries_fall_back_to_frozen_plan():
    from packages.search.query.field_cues import build_query_plan

    for q in (
        "rollout from Fatima Ali",
        "attachment about Cedar move-over",
        "discussion about Cedar migration",
    ):
        assert build_query_plan_v2(q).terms == build_query_plan(q).terms


def test_subject_cue_is_preserved_when_normalization_strips_punctuation():
    plan = build_query_plan_v2(
        "subject: Atlas ranking", normalize=lambda text: text.lower().replace(":", "")
    )
    assert "subject" in plan.cues
    assert all(weights == SUBJECT_SPAN_WEIGHTS for _, weights in plan.terms)
