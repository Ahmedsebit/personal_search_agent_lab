from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from packages.datasets.models import RelevanceJudgment, SearchQuery
from packages.search.models import Email

PEOPLE = [
    "Alice", "Omar", "Priya", "Daniel", "Amina", "Chen", "Ibrahim", "Grace", "Mateo", "Sofia",
    "Noah", "Zuri", "Fatima", "Lucas", "Maya", "Ethan", "Nadia", "Leo", "Hana", "Sam",
    "Ravi", "Lina", "Jon", "Mariam", "Tariq", "Eva", "Ben", "Aya", "Moses", "Nora",
]
PROJECTS = ["Atlas", "Falcon", "Orion", "Nimbus", "Harbor", "Quartz", "Cedar", "Kite", "Lumen", "Delta"]
TOPICS = ["authentication", "ranking", "deployment", "privacy", "latency", "evaluation", "migration", "budget", "design", "incident"]
STATUSES = ["proposal", "review", "decision", "update", "postmortem"]


def build_dataset(email_count: int = 2000, query_count: int = 200, seed: int = 42) -> tuple[list[Email], list[SearchQuery], list[RelevanceJudgment]]:
    rng = random.Random(seed)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    emails: list[Email] = []
    for index in range(email_count):
        sender = rng.choice(PEOPLE)
        recipients = tuple(rng.sample([p for p in PEOPLE if p != sender], k=rng.randint(1, 3)))
        project = rng.choice(PROJECTS)
        topic = rng.choice(TOPICS)
        status = rng.choice(STATUSES)
        sent_at = base + timedelta(hours=index * 3 + rng.randint(0, 2))
        has_attachment = rng.random() < 0.25
        attachment = (f"{project.lower()}-{topic}-{status}.docx",) if has_attachment else ()
        subject = f"{project} {topic} {status}"
        body = (
            f"{sender} shared the {status} for Project {project}. "
            f"The discussion covers {topic}, next steps, owners, and risks. "
            f"Reference phrase: {project} {topic} {status}."
        )
        emails.append(Email(
            id=f"email-{index:05d}", owner_id="user-001", sender=sender,
            recipients=recipients, subject=subject, body=body, sent_at=sent_at,
            has_attachment=has_attachment, attachment_names=attachment,
            thread_id=f"thread-{project.lower()}-{topic}",
            metadata={"project": project, "topic": topic, "status": status},
        ))

    scenarios = ["person", "topic", "person_topic", "recency", "attachment", "thread", "status", "mixed"]
    queries: list[SearchQuery] = []
    judgments: list[RelevanceJudgment] = []
    for index in range(query_count):
        scenario = scenarios[index % len(scenarios)]
        target = emails[(index * 37) % len(emails)]
        project = target.metadata["project"]
        topic = target.metadata["topic"]
        status = target.metadata["status"]
        if scenario == "person": text = f"emails from {target.sender}"
        elif scenario == "topic": text = f"messages about {topic}"
        elif scenario == "person_topic": text = f"{topic} from {target.sender}"
        elif scenario == "recency": text = f"latest {project} {topic}"
        elif scenario == "attachment": text = f"attachment about {project} {topic}"
        elif scenario == "thread": text = f"discussion about {project} {topic}"
        elif scenario == "status": text = f"{status} on {project}"
        else: text = f"latest {status} about {project} {topic} from {target.sender}"
        query = SearchQuery(id=f"query-{index:04d}", text=text, scenario=scenario)
        queries.append(query)
        for email in emails:
            relevance = 0
            if scenario == "person" and email.sender == target.sender: relevance = 2
            elif scenario == "topic" and email.metadata["topic"] == topic: relevance = 2
            elif scenario == "person_topic" and email.sender == target.sender and email.metadata["topic"] == topic: relevance = 3
            elif scenario == "recency" and email.metadata["project"] == project and email.metadata["topic"] == topic: relevance = 2
            elif scenario == "attachment" and email.has_attachment and email.metadata["project"] == project and email.metadata["topic"] == topic: relevance = 3
            elif scenario == "thread" and email.thread_id == target.thread_id: relevance = 3
            elif scenario == "status" and email.metadata["status"] == status and email.metadata["project"] == project: relevance = 3
            elif scenario == "mixed" and email.id == target.id: relevance = 3
            if relevance:
                judgments.append(RelevanceJudgment(query.id, email.id, relevance))
    return emails, queries, judgments
