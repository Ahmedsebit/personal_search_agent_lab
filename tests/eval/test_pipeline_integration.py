import csv
import hashlib
import json
import runpy
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize(
    "stages",
    [
        [{"type": "synonym_expansion"}],
        [{"type": "field_v2"}, {"type": "range_filter"}],
        [{"type": "dense", "encoder": "hashing"}],
        [{"type": "hybrid_rrf", "encoder": "hashing"}],
        [{"type": "rerank", "scorer": "overlap"}],
    ],
)
def test_pipeline_and_gate_clis_run_without_model_downloads(
    stages, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[2]
    emails = tmp_path / "emails.jsonl"
    records = [
        {
            "id": "alice",
            "sender": "Alice Morgan",
            "recipients": ["Grace Lee"],
            "subject": "budget",
            "body": "spend plan",
            "sent_at": "2026-11-23T12:00:00+00:00",
        },
        {
            "id": "fatima",
            "sender": "Fatima Ali",
            "recipients": ["Omar Hassan"],
            "subject": "rollout",
            "body": "deployment plan",
            "sent_at": "2026-11-24T12:00:00+00:00",
        },
    ]
    emails.write_text("\n".join(json.dumps(row) for row in records), encoding="utf-8")
    annotations = tmp_path / "annotations.csv"
    queries = ["spend plan", "subject: rollout", "emails to Grace Lee", "budget yesterday"]
    with annotations.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["query_id", "query"])
        writer.writeheader()
        writer.writerows(
            {"query_id": f"q{index}", "query": query} for index, query in enumerate(queries)
        )
    qrels = tmp_path / "qrels.json"
    qrels.write_text(
        json.dumps({f"q{i}": {"fatima" if i == 1 else "alice": 3} for i in range(len(queries))}),
        encoding="utf-8",
    )
    frozen = tmp_path / "frozen.yaml"
    frozen.write_text(
        yaml.safe_dump({"current": {"id": "E002b", "e003_arm": "control"}}), encoding="utf-8"
    )
    shared = tmp_path / "shared.yaml"
    shared.write_text(
        yaml.safe_dump(
            {
                "data": {"emails": str(emails)},
                "control": {
                    "factory": "packages.search.retrieval.e003_repository:build_control",
                    "normalizer": "control",
                    "tokenizer": "packages.search.retrieval.bm25:tokenize",
                },
                "gain_mode": "exponential",
                "frozen_control": str(frozen),
                "cache_dir": str(tmp_path / "cache"),
                "benchmarks": {
                    "smoke": {
                        "annotations": str(annotations),
                        "qrels": str(qrels),
                        "annotations_sha256": hashlib.sha256(annotations.read_bytes()).hexdigest(),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "pipeline.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "experiment": "SMOKE",
                "shared": str(shared),
                "output_dir": str(tmp_path / "runs"),
                "arms": {"treatment": {"base": "frozen_control", "stages": stages}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("E003_SMOKE", "1")
    for arm in ("control", "treatment"):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_pipeline.py",
                "--config",
                str(config),
                "--arm",
                arm,
                "--benchmark",
                "smoke",
            ],
        )
        runpy.run_path(str(root / "scripts" / "run_pipeline.py"), run_name="__main__")
    treatment = tmp_path / "runs" / "smoke" / "treatment.json"
    run = json.loads(treatment.read_text(encoding="utf-8"))
    assert run["smoke"] is True
    assert len(run["per_query"]) == len(queries)
    assert run["timing"]["warmup"] == 5
    assert run["timing"]["repeats"] == 3
    assert run["timing"]["summary"]["n"] == len(queries)
    assert run["timing"]["machine"]["id"]
    if stages[0]["type"] == "field_v2":
        assert run["per_query"][1]["meta"]["field_v2"]["fired"] is True

    prereg = tmp_path / "gates.yaml"
    prereg.write_text(
        yaml.safe_dump(
            {
                "experiment": "SMOKE",
                "cohorts": {},
                "evaluations": {
                    "smoke": {
                        "annotations": str(annotations),
                        "runs": {
                            arm: str(tmp_path / "runs" / "smoke" / f"{arm}.json")
                            for arm in ("control", "treatment")
                        },
                        "gates": [
                            {
                                "id": "guard",
                                "cohort": "all",
                                "kind": "per_query_retain",
                                "metric": "recall@50",
                            },
                            {
                                "id": "cost",
                                "cohort": "all",
                                "kind": "latency_budget",
                                "stat": "p95",
                                "max_ms": 100000,
                            },
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "results"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_prereg.py",
            "--prereg",
            str(prereg),
            "--out",
            str(output),
        ],
    )
    runpy.run_path(str(root / "scripts" / "evaluate_prereg.py"), run_name="__main__")
    result = json.loads((output / "smoke-results.json").read_text(encoding="utf-8"))
    assert result["smoke"] is True
    assert result["benchmarks"]["smoke"]["cost"]["passed"]
    assert "NOT VALID EVIDENCE" in (output / "smoke-results.md").read_text(encoding="utf-8")


def test_benchmark_extension_is_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "build_benchmark_v2.py"
    records = [
        {
            "id": f"d{index}",
            "sender": "Alice Morgan",
            "recipients": [f"Person Family{index % 20}"],
            "subject": f"budget report {index}",
            "body": "budget",
            "sent_at": (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)).isoformat(),
        }
        for index in range(40)
    ]
    emails = tmp_path / "emails.jsonl"
    emails.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    outputs = [tmp_path / "first", tmp_path / "second"]
    for output in outputs:
        monkeypatch.setattr(
            sys, "argv", [str(script), "--emails", str(emails), "--out", str(output)]
        )
        runpy.run_path(str(script), run_name="__main__")
    assert (outputs[0] / "queries_v2.csv").read_bytes() == (
        outputs[1] / "queries_v2.csv"
    ).read_bytes()
    assert (outputs[0] / "qrels_v2.jsonl").read_bytes() == (
        outputs[1] / "qrels_v2.jsonl"
    ).read_bytes()
    with (outputs[0] / "queries_v2.csv").open(encoding="utf-8", newline="") as handle:
        queries = list(csv.DictReader(handle))
    assert {query["scenario"] for query in queries} == {"recipient", "subject", "date_range"}
    assert all(query["qrels_type"] == "silver" for query in queries)
