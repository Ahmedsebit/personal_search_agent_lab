"""E004 fixed synonym lexicon (preregistered 2026-11-24).

IMPORTANT — provenance: the ten pairs below were identified in the E003 benchmark
audit from the benchmark's own query vocabulary. E004 therefore measures an
*oracle-lexicon upper bound* for vocabulary bridging on this benchmark, not a
general synonym resource. This is stated in the E004 preregistration.
"""

from __future__ import annotations

import re

LEXICON: dict[str, str] = {  # paraphrase -> canonical
    "service disruption": "incident",
    "response time": "latency",
    "rollout": "deployment",
    "sign-in security": "authentication",
    "quality measurement": "evaluation",
    "spend plan": "budget",
    "result ordering": "ranking",
    "move-over": "migration",
    "architecture": "design",
    "data protection": "privacy",
}


def _pairs(bidirectional: bool) -> list[tuple[str, str]]:
    p = list(LEXICON.items())
    if bidirectional:
        p += [(c, para) for para, c in LEXICON.items()]
    return sorted(p, key=lambda kv: -len(kv[0]))  # longest match first


def expand(
    query: str, bidirectional: bool = True, mode: str = "append"
) -> tuple[str, dict[str, object]]:
    """mode='append' (preregistered): keep the query, append the counterpart terms.
    mode='replace' (exploratory): replace the matched phrase with its counterpart."""
    low = query.lower()
    hits: list[dict[str, str]] = []
    taken: list[tuple[int, int]] = []
    for src, dst in _pairs(bidirectional):
        for m in re.finditer(r"(?<![a-z0-9-])" + re.escape(src) + r"(?![a-z0-9-])", low):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            hits.append({"matched": src, "added": dst})
    if not hits:
        return query, {"expansions": []}
    if mode == "replace":
        out = query
        for h in hits:
            out = re.sub(
                r"(?i)(?<![a-z0-9-])" + re.escape(h["matched"]) + r"(?![a-z0-9-])", h["added"], out
            )
        return out, {"expansions": hits, "mode": mode}
    added = []
    for h in hits:
        if h["added"] not in added:
            added.append(h["added"])
    return query + " " + " ".join(added), {"expansions": hits, "mode": mode}
