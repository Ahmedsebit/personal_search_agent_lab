from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from packages.datasets.models import RelevanceJudgment, SearchQuery
from packages.search.models import Email


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def save_dataset(root: Path, emails: list[Email], queries: list[SearchQuery], judgments: list[RelevanceJudgment]) -> None:
    write_jsonl(root / "synthetic" / "emails.jsonl", [
        {**email.__dict__, "sent_at": email.sent_at.isoformat(), "recipients": list(email.recipients), "attachment_names": list(email.attachment_names)} for email in emails
    ])
    write_jsonl(root / "benchmarks" / "queries.jsonl", [query.__dict__ for query in queries])
    write_jsonl(root / "benchmarks" / "judgments.jsonl", [judgment.__dict__ for judgment in judgments])


def load_dataset(root: Path) -> tuple[list[Email], list[SearchQuery], list[RelevanceJudgment]]:
    with (root / "synthetic" / "emails.jsonl").open(encoding="utf-8") as handle:
        emails = []
        for line in handle:
            row = json.loads(line)
            row["sent_at"] = datetime.fromisoformat(row["sent_at"])
            row["recipients"] = tuple(row["recipients"])
            row["attachment_names"] = tuple(row["attachment_names"])
            emails.append(Email(**row))
    with (root / "benchmarks" / "queries.jsonl").open(encoding="utf-8") as handle:
        queries = [SearchQuery(**json.loads(line)) for line in handle]
    with (root / "benchmarks" / "judgments.jsonl").open(encoding="utf-8") as handle:
        judgments = [RelevanceJudgment(**json.loads(line)) for line in handle]
    return emails, queries, judgments
