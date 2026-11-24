"""E003-F deterministic cue routing (preregistered, frozen 2026-11-24).

Turns an (E002b-normalized) query into a field-aware query plan: a list of
(term, {field: weight}) pairs consumed by FieldAwareBM25.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Sequence, Tuple

FIELDS = ("sender", "recipients", "subject", "body", "attachment_names")
DEFAULT_FIELD_WEIGHTS = {"sender": 3.0, "subject": 2.0, "attachment_names": 2.0, "recipients": 1.0, "body": 1.0}
SENDER_SPAN_WEIGHTS = {"sender": 3.0, "subject": 0.0, "attachment_names": 0.0, "recipients": 0.0, "body": 0.0}
ATTACHMENT_TOPIC_WEIGHTS = {"attachment_names": 4.0, "subject": 2.0, "body": 1.0, "sender": 0.0, "recipients": 0.0}
STRUCTURAL_TOKENS = frozenset({"emails", "messages", "from", "attachment", "attachments", "about"})

_ATTACH_RE = re.compile(r"\battachments?\s+about\b", re.IGNORECASE)
_FROM_RE = re.compile(r"\bfrom\b", re.IGNORECASE)


def default_tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass
class QueryPlan:
    terms: List[Tuple[str, Dict[str, float]]]
    cues: List[str] = field(default_factory=list)
    sender_span: List[str] = field(default_factory=list)

    def to_metadata(self) -> dict:
        return {"field_cues": list(self.cues), "sender_span": list(self.sender_span),
                "plan": [[t, w] for t, w in self.terms]}


def build_query_plan(query: str, tokenize: Callable[[str], Sequence[str]] = default_tokenize,
                     field_weights: Dict[str, float] = None, routing: bool = True) -> QueryPlan:
    """Build the frozen E003-F plan.

    routing=False gives the F.a-only exploratory ablation (field weights, no cue routing).
    """
    fw = dict(field_weights or DEFAULT_FIELD_WEIGHTS)
    if not routing:
        return QueryPlan([(t, fw) for t in tokenize(query)])

    cues: List[str] = []
    head, sender_part = query, ""
    m = _FROM_RE.search(query)
    if m:
        cues.append("sender")
        head, sender_part = query[: m.start()], query[m.end():]
    attach = bool(_ATTACH_RE.search(head))
    if attach:
        cues.append("attachment")

    terms: List[Tuple[str, Dict[str, float]]] = []
    if attach:
        am = _ATTACH_RE.search(head)
        pre, topic = head[: am.start()], head[am.end():]
        for t in tokenize(pre):
            if t not in STRUCTURAL_TOKENS:
                terms.append((t, fw))
        for t in tokenize(topic):
            if t not in STRUCTURAL_TOKENS:
                terms.append((t, dict(ATTACHMENT_TOPIC_WEIGHTS)))
    else:
        for t in tokenize(head):
            if cues and t in STRUCTURAL_TOKENS:
                continue
            terms.append((t, fw))
    span = [t for t in tokenize(sender_part) if t not in STRUCTURAL_TOKENS]
    for t in span:
        terms.append((t, dict(SENDER_SPAN_WEIGHTS)))
    return QueryPlan(terms, cues, span)
