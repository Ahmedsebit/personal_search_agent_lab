"""E009 — grounded answers built from the top retrieved emails, with inline citations [doc_id].

Answerers
  ExtractiveAnswerer   offline default: cites the most query-relevant sentences of the top-k emails.
  LLMAnswerer          optional (E009b): uses a relevance-judge provider; must cite.
reference_answer      a clean gold-relevant answer used as the base for planted failures.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import NotRequired, Protocol, TypedDict

from packages.eval.labeling.llm_judge import Provider


class Sentence(TypedDict):
    text: str
    citations: list[str]


class Answer(TypedDict):
    text: str
    sentences: list[Sentence]
    answerer: NotRequired[str]


class Answerer(Protocol):
    name: str

    def answer(self, query: str, retrieved: Sequence[dict[str, str]]) -> Answer: ...


STOP = set(
    """a an the of to in on for from about and or with by at is are was were be been
this that these those emails email messages message discussion latest newest recent most
earliest oldest first last any all
attachment subject me my our your what who when which please update notes re fw fwd""".split()
)
CITE = re.compile(r"\[([A-Za-z0-9_.:\-]+)\]")


def content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 3]


def doc_text(d: dict[str, str]) -> str:
    return f"{d.get('subject', '')}. {d.get('body', '')}"


SEG = re.compile(r"([^\[]*?)\s*((?:\[[A-Za-z0-9_.:\-]+\]\s*[.!?]?\s*)+)|([^\[]+)$")


def parse_answer(text: str) -> list[Sentence]:
    """Citations attach to the sentence they FOLLOW ("Text. [d1]" and "Text [d1]." both work)."""
    out: list[Sentence] = []
    for m in SEG.finditer(text.strip()):
        body, cites, tail = m.group(1), m.group(2), m.group(3)
        if tail is not None:
            out += [
                {"text": x.strip(), "citations": []}
                for x in re.split(r"(?<=[.!?])\s+|\n+", tail)
                if x.strip()
            ]
            continue
        parts = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", body or "") if x.strip()]
        if not parts and cites and out:
            out[-1]["citations"] += CITE.findall(cites)
            continue
        out += [{"text": x, "citations": []} for x in parts[:-1]]
        if parts:
            last = parts[-1].rstrip()
            if re.search(r"[.!?]\s*$", cites or "") and not re.search(r"[.!?]$", last):
                last += "."
            out.append({"text": last, "citations": CITE.findall(cites)})
    return [x for x in out if x["text"] or x["citations"]]


def render(sents: list[Sentence]) -> str:
    return " ".join(
        f"{s['text']} " + "".join(f"[{c}]" for c in s["citations"]) for s in sents
    ).strip()


def _best_sentence(query_words: set[str], d: dict[str, str]) -> tuple[str | None, int]:
    best, score = None, -1
    for s in sentences(doc_text(d)):
        sc = len(query_words & set(content_words(s)))
        if sc > score:
            best, score = s, sc
    return best, score


class ExtractiveAnswerer:
    name = "extractive-v1"

    def __init__(self, k: int = 5, max_sentences: int = 3) -> None:
        self.k, self.max_sentences = k, max_sentences

    def answer(self, query: str, retrieved: Sequence[dict[str, str]]) -> Answer:
        qw = set(content_words(query))
        cands = []
        for rank, d in enumerate(retrieved[: self.k]):
            s, sc = _best_sentence(qw, d)
            if s and sc > 0:
                cands.append((-sc, rank, s, d["doc_id"]))
        cands.sort()
        sents: list[Sentence] = [
            {"text": s.rstrip(".") + ".", "citations": [did]}
            for _, _, s, did in cands[: self.max_sentences]
        ]
        if not sents and retrieved:
            d = retrieved[0]
            sents = [
                {
                    "text": (d.get("subject") or "See the top email").rstrip(".") + ".",
                    "citations": [d["doc_id"]],
                }
            ]
        return {"text": render(sents), "sentences": sents, "answerer": self.name}


class LLMAnswerer:
    PROMPT = """Answer the user's search request using ONLY the emails below.
Every sentence must end with the [doc_id] of the email(s) it comes from.
Do not add facts, names, numbers or contact details absent from the cited email.
At most 3 sentences.
REQUEST: {query}
EMAILS:
{emails}"""

    def __init__(self, provider: Provider, k: int = 5) -> None:
        self.p, self.k, self.name = provider, k, f"llm:{getattr(provider, 'name', 'provider')}"

    def answer(self, query: str, retrieved: Sequence[dict[str, str]]) -> Answer:
        emails = "\n".join(
            f"[{d['doc_id']}] From {d.get('sender', '')} | {d.get('date', '')} | "
            f"{d.get('subject', '')}: "
            f"{d.get('body', '')[:800]}"
            for d in retrieved[: self.k]
        )
        text, _ = self.p.complete(self.PROMPT.format(query=query, emails=emails))
        sents = parse_answer(text)
        return {"text": render(sents), "sentences": sents, "answerer": self.name}


def reference_answer(
    query: str,
    relevant: dict[str, float],
    docs_by_id: dict[str, dict[str, str]],
    ts: dict[str, datetime | None],
    newest_first: bool = True,
    k: int = 3,
) -> Answer:
    """Gold-relevant emails ordered by grade, then recency in the requested direction."""
    ids = [d for d in relevant if d in docs_by_id and relevant[d] > 0]
    ids.sort(
        key=lambda d: (
            -relevant[d],
            -(timestamp.timestamp() if (timestamp := ts.get(d)) else 0)
            * (1 if newest_first else -1),
            d,
        )
    )
    qw = set(content_words(query))
    sents: list[Sentence] = []
    for d in ids[:k]:
        s, sc = _best_sentence(qw, docs_by_id[d])
        s = s if (s and sc > 0) else (docs_by_id[d].get("subject") or "")
        if s:
            sents.append({"text": s.rstrip(".") + ".", "citations": [d]})
    return {"text": render(sents), "sentences": sents, "answerer": "reference"}
