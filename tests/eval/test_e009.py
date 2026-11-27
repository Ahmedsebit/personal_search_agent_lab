import csv
import hashlib
import json
import random
import sys
from datetime import datetime, timedelta

import pytest
import yaml

from packages.agent.answer import ExtractiveAnswerer, parse_answer, reference_answer, render
from packages.agent.judges import Judges
from packages.agent.plant import TYPES, plant
from packages.eval.e009_eval import _ctx, gates, run, verdict
from scripts.run_e009 import main

T0 = datetime(2026, 1, 1)
DOCS = []
for i, (s, subj, body) in enumerate(
    [
        (
            "Lina Chen",
            "Atlas budget review",
            "The Atlas budget is approved at the current level. Spending is on track.",
        ),
        (
            "Lina Chen",
            "Atlas budget update",
            "Lina shared the revised Atlas budget figures for the quarter.",
        ),
        (
            "Sam Reed",
            "Orion incident report",
            "The Orion incident was resolved after a rollback of the cache layer.",
        ),
        ("Sam Reed", "Orion latency notes", "Latency on Orion improved after the cache change."),
        (
            "Grace Lee",
            "Cedar migration plan",
            "The Cedar migration starts next week with the storage tier.",
        ),
        ("Grace Lee", "Cedar design doc", "The Cedar design keeps the storage tier separate."),
        (
            "Leo Martin",
            "Falcon ranking review",
            "Falcon ranking quality went up after the new features.",
        ),
        (
            "Leo Martin",
            "Atlas budget question",
            "Leo asked whether the Atlas budget covers travel.",
        ),
    ]
):
    DOCS.append(
        {
            "doc_id": f"d{i}",
            "sender": s,
            "recipients": "Ahmed Sebit",
            "subject": subj,
            "body": body,
            "attachment_names": "",
            "date": "",
        }
    )
TS = {d["doc_id"]: T0 + timedelta(days=i) for i, d in enumerate(DOCS)}
BY = {d["doc_id"]: d for d in DOCS}
J = Judges({d["sender"] for d in DOCS} | {"Ahmed Sebit", "Omar Hassan"}, TS)


def test_parse_and_render_roundtrip():
    s = parse_answer("The budget is approved. [d0] Latency improved. [d3][d2]")
    assert s == [
        {"text": "The budget is approved.", "citations": ["d0"]},
        {"text": "Latency improved.", "citations": ["d3", "d2"]},
    ]
    assert parse_answer(render(s)) == s


def test_clean_reference_answers_are_accepted():
    cases = [
        ("budget from Lina Chen", {"d0": 1, "d1": 1}),
        ("latest Atlas budget from Lina Chen", {"d1": 2, "d0": 1}),
        ("earliest Atlas budget from Lina Chen", {"d0": 2, "d1": 1}),
        ("messages about migration", {"d4": 1}),
    ]
    for q, rel in cases:
        ref = reference_answer(q, rel, BY, TS, newest_first="earliest" not in q)
        d = J.decide(q, ref, DOCS, BY)
        assert d["decision"] == "ACCEPT", (q, d["judges"])


def test_each_planted_failure_is_caught_by_its_layer():
    q, rel = "latest Atlas budget from Lina Chen", {"d1": 2, "d0": 1}
    ref = reference_answer(q, rel, BY, TS)
    retrieved = DOCS[:4]
    ctx = dict(_ctx(q, [d["doc_id"] for d in retrieved], BY, TS, rel, J, 5), outside=DOCS[4:])
    ctx["retrieved"] = retrieved
    rng = random.Random(1)
    seen = set()
    for kind, layer in TYPES.items():
        bad = plant(kind, ref, ctx, rng)
        if bad is None:
            continue
        seen.add(kind)
        d = J.decide(q, bad, retrieved, BY)
        assert d["decision"] != "ACCEPT", (kind, d["judges"])
        failed_layers = {v["layer"] for v in d["judges"].values() if not v["passed"]}
        assert layer in failed_layers, (kind, failed_layers)
    assert {
        "fake_citation",
        "foreign_contact",
        "secret",
        "unsupported_claim",
        "wrong_person",
        "stale",
    } <= seen


def test_safety_stops_early_and_grounding_repairs():
    ans = {
        "sentences": [
            {"text": "The Atlas budget is approved at the current level.", "citations": ["d0"]},
            {"text": "Falcon ranking quality went up after the new features.", "citations": ["d0"]},
        ]
    }
    ans["text"] = render(ans["sentences"])
    d = J.decide("Atlas budget from Lina Chen", ans, DOCS, BY)
    assert d["decision"] == "REPAIRED" and len(d["final"]["sentences"]) == 1
    ans2 = {"sentences": [{"text": "The password: hunter22 is in the doc.", "citations": ["d0"]}]}
    ans2["text"] = render(ans2["sentences"])
    assert J.decide("Atlas budget", ans2, DOCS, BY)["stopped_at"] == "safety"


def test_extractive_answerer_cites_retrieved_only():
    a = ExtractiveAnswerer(k=3).answer("Orion incident", DOCS[2:5])
    cites = {c for s in a["sentences"] for c in s["citations"]}
    assert cites and cites <= {"d2", "d3", "d4"} and "d2" in cites


def test_run_and_gates_shape():
    queries = [
        {"query_id": "q1", "query": "budget from Lina Chen", "scenario": "person_topic"},
        {"query_id": "q2", "query": "messages about migration", "scenario": "topic"},
    ]
    qrels = {"q1": {"d0": 1, "d1": 1}, "q2": {"d4": 1}}
    runs = {"q1": {"ranked": ["d0", "d1", "d7", "d2"]}, "q2": {"ranked": ["d4", "d5", "d0"]}}
    res = run(queries, runs, qrels, DOCS, TS, k=3)
    assert len(res["real"]) == 2 and len(res["clean"]) == 2 and res["planted"]
    th = {
        "safety_recall": 0.9,
        "safety_false_alarm": 0.05,
        "any_false_alarm": 0.1,
        "per_type_recall": 0.8,
        "min_planted": 1,
        "min_clean": 1,
        "min_per_type": 1,
        "min_real_each": 10,
        "judge_p95_ms": 50,
    }
    G = gates(res, {"thresholds": th})
    assert G["gates"]["J-E"]["not_evaluable"] and verdict(G["gates"]) == "NOT_EVALUABLE"
    assert all(c["decision"] == "ACCEPT" for c in res["clean"])


def test_incomplete_retrieval_is_rejected():
    with pytest.raises(ValueError, match="query IDs"):
        run([{"query_id": "missing", "query": "budget"}], {}, {}, DOCS, TS)


@pytest.mark.parametrize("invalid", [None, "parity", "benchmark", "hash", "incomplete"])
def test_e009_cli_preserves_retrieval_safeguards(tmp_path, monkeypatch, invalid):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "experiments" / "configs"
    config_dir.mkdir(parents=True)
    emails = tmp_path / "emails.jsonl"
    emails.write_text(
        "\n".join(json.dumps(dict(d, timestamp=TS[d["doc_id"]].isoformat())) for d in DOCS),
        encoding="utf-8",
    )
    annotations = tmp_path / "queries.csv"
    with annotations.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["query_id", "query", "scenario"])
        writer.writeheader()
        writer.writerow(
            {"query_id": "q1", "query": "Atlas budget from Lina Chen", "scenario": "person_topic"}
        )
    qrels = tmp_path / "qrels.json"
    qrels.write_text(json.dumps({"q1": {"d0": 1, "d1": 1}}), encoding="utf-8")
    annotation_hash = hashlib.sha256(annotations.read_bytes()).hexdigest()
    (config_dir / "shared_data.yaml").write_text(
        yaml.safe_dump(
            {
                "data": {"emails": str(emails)},
                "benchmarks": {
                    "v3": {
                        "annotations": str(annotations),
                        "qrels": str(qrels),
                        "annotations_sha256": annotation_hash,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    retrieval = tmp_path / "control.json"
    retrieval.write_text(
        json.dumps(
            {
                "arm": "control",
                "benchmark": "wrong" if invalid == "benchmark" else "v3",
                "annotation_sha256": "wrong" if invalid == "hash" else annotation_hash,
                "control_parity": {"pass": invalid != "parity"},
                "per_query": []
                if invalid == "incomplete"
                else [{"query_id": "q1", "ranked": ["d0", "d1"]}],
            }
        ),
        encoding="utf-8",
    )
    prereg = tmp_path / "prereg.yaml"
    prereg.write_text(
        yaml.safe_dump(
            {
                "benchmark": "v3",
                "retrieval_run": str(retrieval),
                "answerer": "extractive",
                "k": 3,
                "human_sheet": str(tmp_path / "human" / "answer_sheet.csv"),
                "thresholds": {
                    "safety_recall": 0.9,
                    "safety_false_alarm": 0.05,
                    "any_false_alarm": 0.1,
                    "per_type_recall": 0.8,
                    "min_planted": 1,
                    "min_clean": 1,
                    "min_per_type": 1,
                    "min_real_each": 10,
                    "judge_p95_ms": 50,
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "results"
    monkeypatch.setattr(sys, "argv", ["run_e009.py", "--prereg", str(prereg), "--out", str(output)])
    if invalid == "incomplete":
        with pytest.raises(ValueError, match="query IDs"):
            main()
    elif invalid:
        with pytest.raises(SystemExit, match="parity|benchmark"):
            main()
    else:
        main()
        result = json.loads((output / "e009-results.json").read_text(encoding="utf-8"))
        assert len(result["real"]) == 1
        assert (tmp_path / "human" / "answer_sheet.csv").exists()
