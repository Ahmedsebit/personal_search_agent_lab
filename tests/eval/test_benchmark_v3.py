import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.build_benchmark_v3 import cues, dedupe_v1, new_silver


def test_cues():
    c = cues("earliest budget from Lina Chen")
    assert (
        c["temporal_operator"] == "earliest"
        and c["temporal_direction"] == "oldest"
        and c["field_sender_cue"] == 1
    )
    assert cues("most recent incident")["temporal_operator"] == "most recent"
    assert cues("spreadsheet about Cedar migration")["field_attachment_cue"] == 1
    assert cues("emails to Sam Reed")["field_recipient_cue"] == 1


def test_dedupe_keeps_one_and_flags_conflicts():
    ann = [
        {"query_id": "a", "query": "X"},
        {"query_id": "b", "query": "x "},
        {"query_id": "c", "query": "Y"},
        {"query_id": "d", "query": "y"},
    ]
    q = {"a": {"d1": 1}, "b": {"d1": 1}, "c": {"d1": 1}, "d": {"d2": 1}}
    keep, removed, conflicts = dedupe_v1(ann, q)
    assert removed == ["b"] and conflicts == ["y"] and len(keep) == 3 and keep[0][1] == 2


def test_new_silver_grades_extreme_email():
    t0 = datetime(2026, 1, 1)
    docs, ts = [], {}
    for i in range(6):
        docs.append(
            {
                "doc_id": f"d{i}",
                "sender": "Lina Chen",
                "recipients": "",
                "subject": "budget",
                "body": "budget plan",
                "attachment_names": "Atlas_budget.xlsx" if i < 3 else "",
            }
        )
        ts[f"d{i}"] = t0 + timedelta(days=i)
    out = new_silver(docs, ts, random.Random(1))
    kinds = {s for s, _, _ in out}
    assert {"attachment_file", "temporal_newest", "temporal_oldest"} <= kinds
    for s, _text, rel in out:
        if s == "temporal_newest":
            assert rel["d5"] == 2 and all(g == 1 for d, g in rel.items() if d != "d5")
        if s == "temporal_oldest":
            assert rel["d0"] == 2
        if s == "attachment_file":
            assert set(rel) == {"d0", "d1", "d2"}
