import json
import math
import runpy
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from packages.common.config import load_yaml
from packages.datasets.loader import save_dataset
from packages.datasets.models import RelevanceJudgment, SearchQuery
from packages.eval.e002b_runner_support import (
    RETRIEVER_TYPE,
    build_e002b_retriever,
    e002b_query_metadata,
    register_e002b_retriever,
)
from packages.search.models import Email


def test_runner_registration() -> None:
    registry = {}
    register_e002b_retriever(registry)
    assert registry[RETRIEVER_TYPE] is build_e002b_retriever


def test_runner_builds_retriever_and_serializes_metadata() -> None:
    config = {
        "retrieval": {
            "bm25": {"k1": 1.5, "b": 0.75},
        }
    }
    retriever = build_e002b_retriever(
        {
            "alice": "Alice Morgan budget",
            "fatima": "Fatima Ali rollout",
        },
        config,
        aliases={"ali": ("alice", "morgan")},
        known_full_names=(("fatima", "ali"),),
    )
    result = retriever.search("rollout from Fatima Ali")
    metadata = e002b_query_metadata(result)

    assert metadata["source"] == "context-aware-query-normalized-bm25"
    assert metadata["cohorts"] == ["alias_collision"]
    assert metadata["suppressed_aliases"][0]["phrase"] == "fatima ali"


def test_runner_forwards_bm25_parameters() -> None:
    retriever = build_e002b_retriever(
        {"alice": "Alice Morgan budget", "fatima": "Fatima Ali rollout rollout"},
        {"retrieval": {"bm25": {"k1": 0.0, "b": 0.0}}},
        aliases={},
        known_full_names=(),
    )

    result = retriever.search("rollout")

    assert [hit.document_id for hit in result.hits] == ["fatima"]
    assert result.hits[0].score == pytest.approx(math.log(2))


@pytest.mark.parametrize(
    "config_name",
    [
        "001_bm25.yaml",
        "005_query_normalized_bm25.yaml",
        "006_context_aware_query_normalized_bm25.yaml",
    ],
)
def test_experiment_config_runs_end_to_end(
    config_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "experiments" / "configs" / config_name)
    config["dataset"]["root"] = str(tmp_path / "datasets")
    config["report"]["output_dir"] = str(tmp_path / "results")
    config["retrieval"]["top_k"] = 1
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    emails = [
        Email("alice", "u", "Alice Morgan", (), "budget", "proposal", now),
        Email("fatima", "u", "Fatima Ali", (), "rollout", "plan", now),
    ]
    queries = [
        SearchQuery("collision", "rollout from Fatima Ali", "person_topic"),
        SearchQuery("alias", "emails from Ali", "person"),
        SearchQuery("none", "budget proposal", "topic"),
        SearchQuery("typo", "budegt", "topic"),
    ]
    judgments = [
        RelevanceJudgment(query.id, "fatima" if query.id == "collision" else "alice", 3)
        for query in queries
    ]
    save_dataset(Path(config["dataset"]["root"]), emails, queries, judgments)
    monkeypatch.setattr(sys, "argv", ["run_experiment.py", "--config", str(config_path)])

    runpy.run_path(str(root / "scripts" / "run_experiment.py"), run_name="__main__")

    report_path = tmp_path / "results" / f"{config['name']}.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["query_count"] == len(queries)
    assert report_path.with_suffix(".md").is_file()
    assert all(len(row["ranked_ids"]) <= 1 for row in report["per_query"])
    collision, alias, none, typo = report["per_query"]
    if config["retrieval"]["type"] == RETRIEVER_TYPE:
        assert report["retriever"] == "context-aware-query-normalized-bm25"
        assert collision["ranked_ids"] == ["fatima"]
        assert collision["cohorts"] == ["alias_collision"]
        assert collision["suppressed_aliases"][0]["phrase"] == "fatima ali"
        assert "morgan" not in collision["normalized_terms"]
        assert alias["ranked_ids"] == ["alice"]
        assert alias["cohorts"] == ["alias"]
        assert none["cohorts"] == []
        assert none["ranked_ids"] == ["alice"]
        assert typo["ranked_ids"] == ["alice"]
        assert typo["cohorts"] == ["misspelling"]
    else:
        assert "suppressed_aliases" not in collision
