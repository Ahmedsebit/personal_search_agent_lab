"""E003-T temporal-intent detection (preregistered, frozen 2026-11-24).

Closed lexicon only: latest, newest, most recent, recent.
Range/relative expressions (last week, yesterday, today, dates) are OUT OF SCOPE
and are deliberately not detected.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TEMPORAL_LEXICON = ("most recent", "latest", "newest", "recent")  # longest first
_PATTERN = re.compile(r"\b(" + "|".join(re.escape(t) for t in TEMPORAL_LEXICON) + r")\b", re.IGNORECASE)


@dataclass(frozen=True)
class TemporalIntent:
    original_query: str
    stripped_query: str
    fired: bool
    operators: tuple = field(default_factory=tuple)

    def to_metadata(self) -> dict:
        return {"temporal_fired": self.fired, "temporal_operators": list(self.operators),
                "stripped_query": self.stripped_query}


def detect_temporal_intent(query: str) -> TemporalIntent:
    ops = tuple(m.group(1).lower() for m in _PATTERN.finditer(query))
    if not ops:
        return TemporalIntent(query, query, False, ())
    stripped = re.sub(r"\s+", " ", _PATTERN.sub(" ", query)).strip()
    return TemporalIntent(query, stripped, True, ops)
