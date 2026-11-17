from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from packages.datasets.models import RelevanceJudgment, SearchQuery
from packages.search.models import Email

PEOPLE = ["Alice Morgan", "Alice Moreno", "Omar Hassan", "Omar Hussein", "Priya Shah", "Daniel Kim", "Amina Yusuf", "Chen Wei", "Ibrahim Noor", "Grace Lee", "Mateo Silva", "Sofia Rossi", "Noah Williams", "Zuri Kamau", "Fatima Ali", "Lucas Meyer", "Maya Patel", "Ethan Brown", "Nadia Said", "Leo Martin", "Hana Okafor", "Sam Reed", "Ravi Gupta", "Lina Chen", "Jon Bell", "Mariam Musa", "Tariq Aziz", "Eva Novak", "Ben Clarke", "Aya Nasser"]
PROJECTS = ["Atlas", "Atlassian", "Falcon", "Falcone", "Orion", "OrionX", "Nimbus", "Harbor", "Quartz", "Cedar"]
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
        if scenario == "attachment" and not target.has_attachment:
            target = next(e for e in emails if e.has_attachment)
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
        difficulty = ("easy", "medium", "hard")[(index // 8) % 3]
        aliases = {"Alice Morgan":"Ali", "Alice Moreno":"Ally", "Omar Hassan":"OH", "Omar Hussein":"O.H.", "Daniel Kim":"Dan"}
        paraphrases = {"authentication":"sign-in security", "ranking":"result ordering", "deployment":"rollout", "privacy":"data protection", "latency":"response time", "evaluation":"quality measurement", "migration":"move-over", "budget":"spend plan", "design":"architecture", "incident":"service disruption"}
        misspellings = {"authentication":"authentcation", "ranking":"rankng", "deployment":"deplyoment", "privacy":"privcy", "latency":"latncy", "evaluation":"evalution", "migration":"migraton", "budget":"budegt", "design":"desgin", "incident":"incdient"}
        if difficulty != "easy":
            for canonical, alias in aliases.items(): text = text.replace(canonical, alias)
            for canonical, paraphrase in paraphrases.items(): text = text.replace(canonical, paraphrase)
        if difficulty == "hard":
            for canonical, typo in misspellings.items(): text = text.replace(canonical, typo)
        query = SearchQuery(id=f"query-{index:04d}", text=text, scenario=scenario, difficulty=difficulty, intent={"project": project, "topic": topic, "sender": target.sender, "status": status}, notes="Benchmark v2")
        queries.append(query)
        for email in emails:
            relevance = 0
            if scenario == "person" and email.sender == target.sender: relevance = 2
            elif scenario == "topic" and email.metadata["topic"] == topic: relevance = 2
            elif scenario == "person_topic" and email.sender == target.sender and email.metadata["topic"] == topic: relevance = 3
            elif scenario == "recency" and email.metadata["project"] == project and email.metadata["topic"] == topic:
                matching = [e for e in emails if e.metadata["project"] == project and e.metadata["topic"] == topic]
                relevance = 3 if email.id == max(matching, key=lambda e: e.sent_at).id else 1
            elif scenario == "attachment" and email.has_attachment and email.metadata["project"] == project and email.metadata["topic"] == topic: relevance = 3
            elif scenario == "thread" and email.thread_id == target.thread_id: relevance = 3
            elif scenario == "status" and email.metadata["status"] == status and email.metadata["project"] == project: relevance = 3
            elif scenario == "mixed" and email.id == target.id: relevance = 3
            if relevance:
                judgments.append(RelevanceJudgment(query.id, email.id, relevance, "explicit scenario constraints"))
    return emails, queries, judgments
