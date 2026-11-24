import json

import pytest

from packages.search.data.e003_corpus import load_qrels, resolve_fields, to_field_documents
from packages.search.retrieval import e003_wiring as wiring
from packages.search.retrieval.e003_repository import build_control


def test_repository_control_preserves_alias_protection_and_bm25_parameters():
    records = [
        {
            "id": "alice",
            "sender": "Alice Morgan",
            "recipients": ["Grace Lee", "Omar Hassan"],
            "subject": "budget",
            "body": "proposal",
        },
        {
            "id": "fatima",
            "sender": "Fatima Ali",
            "recipients": ["Grace Lee"],
            "subject": "rollout",
            "body": "rollout plan",
        },
    ]
    control = build_control(records)
    search = wiring.make_search_fn(control)
    normalize = wiring.make_normalizer("control", retriever=control)

    assert search("rollout from Fatima Ali", 1)[0][0] == "fatima"
    assert search("budget from Ali", 1)[0][0] == "alice"
    assert "morgan" not in normalize("rollout from Fatima Ali").split()
    assert "morgan" in normalize("emails from Ali").split()
    assert wiring.resolve_bm25_params(control, 99.0, 99.0)[:2] == (1.5, 0.75)
    fields = to_field_documents(records, resolve_fields(records))
    assert fields[0]["recipients"] == "Grace Lee; Omar Hassan"


@pytest.mark.parametrize("count", [1, 2])
def test_native_qrels_document_ids_are_loaded(tmp_path, count):
    path = tmp_path / "judgments.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"query_id": "q1", "document_id": "alice", "relevance": 3},
                {"query_id": "q1", "document_id": "fatima", "relevance": 1},
            ][:count]
        ),
        encoding="utf-8",
    )
    expected = {"alice": 3.0}
    if count == 2:
        expected["fatima"] = 1.0
    assert load_qrels(str(path)) == {"q1": expected}


def test_control_normalizer_requires_its_retriever():
    with pytest.raises(ValueError, match="retriever instance"):
        wiring.make_normalizer("control")
