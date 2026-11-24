from datetime import datetime, timezone
import pytest
from packages.search.retrieval.temporal_rerank import recency_rerank, FROZEN_LAMBDA


def ts(day):
    return datetime(2026, 1, day, tzinfo=timezone.utc)


def test_frozen_lambda():
    assert FROZEN_LAMBDA == 0.30


def test_newer_wins_when_lexical_close():
    out = recency_rerank([("old", 10.0), ("new", 9.5), ("low", 1.0)], {"old": ts(1), "new": ts(20), "low": ts(5)})
    assert [d for d, _ in out][:2] == ["new", "old"]


def test_lexical_dominates_when_gap_large():
    out = recency_rerank([("rel", 10.0), ("x", 1.0), ("newest", 0.0)], {"rel": ts(1), "x": ts(2), "newest": ts(30)})
    assert out[0][0] == "rel"


def test_lambda_zero_preserves_lexical_order():
    c = [("a", 3.0), ("b", 2.0), ("c", 1.0)]
    assert [d for d, _ in recency_rerank(c, {"a": ts(1), "b": ts(2), "c": ts(3)}, lam=0.0)] == ["a", "b", "c"]


def test_deterministic_ties_and_single_candidate():
    c = [("b", 1.0), ("a", 1.0)]
    t = {"a": ts(1), "b": ts(1)}
    assert recency_rerank(c, t) == recency_rerank(list(reversed(c)), t)
    assert recency_rerank([("only", 2.0)], {"only": ts(1)}) == [("only", 1.0)]


def test_missing_timestamp_raises():
    with pytest.raises(ValueError):
        recency_rerank([("a", 1.0)], {"a": None})
