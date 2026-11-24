from datetime import datetime, timezone
import pytest
from packages.search.retrieval.e003_retrievers import E003Retriever
from packages.search.retrieval.field_aware_bm25 import FieldAwareBM25

DOCS = [
    {"doc_id": "a", "sender": "Fatima Ali", "subject": "Atlas ranking", "body": "atlas ranking review", "attachment_names": "", "recipients": ""},
    {"doc_id": "b", "sender": "Leo Martin", "subject": "Atlas ranking", "body": "atlas ranking update", "attachment_names": "", "recipients": ""},
    {"doc_id": "c", "sender": "Leo Martin", "subject": "Cedar", "body": "cedar notes", "attachment_names": "cedar-move-over.xlsx", "recipients": ""},
]
TS = {"a": datetime(2026, 1, 1, tzinfo=timezone.utc), "b": datetime(2026, 3, 1, tzinfo=timezone.utc),
      "c": datetime(2026, 2, 1, tzinfo=timezone.utc)}
CALLS = []


def control(q, k):
    CALLS.append(q)
    base = {"atlas ranking": [("a", 5.0), ("b", 4.9), ("c", 0.0)], "cedar notes": [("c", 2.0)]}
    return base.get(q.lower(), [("a", 1.0), ("b", 0.5), ("c", 0.1)])[:k]


def test_t_arm_non_temporal_is_identical_to_control():
    r = E003Retriever("e003_t", control_search=control, timestamps=TS)
    for q in ("cedar notes", "emails from Leo Martin", "Atlas ranking"):
        assert r.search(q, 50)[0] == control(q, 50)


def test_t_arm_strips_and_reranks_temporal():
    CALLS.clear()
    r = E003Retriever("e003_t", control_search=control, timestamps=TS)
    ranked, meta = r.search("latest Atlas ranking", 50)
    assert CALLS[0] == "Atlas ranking" and meta["temporal_fired"]
    assert [d for d, _ in ranked] == ["b", "a", "c"]


def test_f_arm_uses_normalizer_and_routing():
    idx = FieldAwareBM25(DOCS)
    r = E003Retriever("e003_f", control_search=control, field_index=idx, normalize=lambda q: q + " alice")
    ranked, meta = r.search("emails from Fatima Ali", 50)
    assert ranked[0][0] == "a" and meta["sender_span"] == ["fatima", "ali", "alice"]


def test_ft_combines():
    idx = FieldAwareBM25(DOCS)
    r = E003Retriever("e003_ft", control_search=control, field_index=idx, timestamps=TS)
    ranked, meta = r.search("latest Atlas ranking", 50)
    assert meta["temporal_fired"] and meta["plan"] and ranked[0][0] == "b"


def test_arm_requirements_enforced():
    with pytest.raises(ValueError):
        E003Retriever("e003_f", control_search=control)
    with pytest.raises(ValueError):
        E003Retriever("e003_t", control_search=control)
    with pytest.raises(ValueError):
        E003Retriever("e004", control_search=control)
