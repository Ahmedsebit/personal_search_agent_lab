"""E005 cue extension: recipient and subject cues (E003 field_cues stays frozen).

  'emails to <person>'        -> person terms on recipients only
  'subject: <words>' / 'titled <words>' -> words on subject only (weight 3)
Everything else falls back to the frozen E003 plan.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from packages.search.query.field_cues import (
    DEFAULT_FIELD_WEIGHTS,
    STRUCTURAL_TOKENS,
    QueryPlan,
    build_query_plan,
    default_tokenize,
)

RECIPIENT_SPAN_WEIGHTS = {
    "recipients": 3.0,
    "sender": 0.0,
    "subject": 0.0,
    "body": 0.0,
    "attachment_names": 0.0,
}
SUBJECT_SPAN_WEIGHTS = {
    "subject": 3.0,
    "sender": 0.0,
    "recipients": 0.0,
    "body": 0.0,
    "attachment_names": 0.0,
}
_TO = re.compile(
    r"\b(?:emails|messages)\s+(?:sent\s+)?to\s+(.+?)(?=\s+(?:about|from)\b|$)", re.IGNORECASE
)
_SUBJ = re.compile(r"\b(?:subject:\s*|titled\s+)(.+?)(?=\s+(?:from|to)\b|$)", re.IGNORECASE)


def build_query_plan_v2(
    query: str,
    tokenize: Callable[[str], list[str]] = default_tokenize,
    field_weights: dict[str, float] | None = None,
    normalize: Callable[[str], str] = lambda q: q,
) -> QueryPlan:
    field_weights = field_weights or DEFAULT_FIELD_WEIGHTS
    to, subj = _TO.search(query), _SUBJ.search(query)
    if not to and not subj:
        return build_query_plan(normalize(query), tokenize, field_weights)
    spans, cues, rest = [], [], query
    for m, w, cue in (
        (to, RECIPIENT_SPAN_WEIGHTS, "recipient"),
        (subj, SUBJECT_SPAN_WEIGHTS, "subject"),
    ):
        if m:
            cues.append(cue)
            spans.append((m.group(1), w))
            rest = rest.replace(m.group(0), " ")
    base = build_query_plan(normalize(rest), tokenize, field_weights)
    terms = [
        (t, w)
        for t, w in base.terms
        if t not in STRUCTURAL_TOKENS | {"to", "sent", "subject", "titled"}
    ]
    for text, w in spans:
        terms += [(t, dict(w)) for t in tokenize(normalize(text)) if t not in STRUCTURAL_TOKENS]
    return QueryPlan(terms, base.cues + cues, base.sender_span)
