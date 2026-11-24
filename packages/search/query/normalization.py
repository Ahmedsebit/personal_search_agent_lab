from __future__ import annotations

import re
from dataclasses import dataclass

# E002 rules are benchmark-owned and explicit. No fuzzy matching or semantics.
ALIASES: dict[str, tuple[str, ...]] = {
    "ali": ("alice", "morgan"),
    "ally": ("alice", "moreno"),
    "oh": ("omar", "hassan", "omar", "hussein"),
    "dan": ("daniel", "kim"),
}

MISSPELLINGS: dict[str, str] = {
    "authentcation": "authentication",
    "rankng": "ranking",
    "deplyoment": "deployment",
    "privcy": "privacy",
    "latncy": "latency",
    "evalution": "evaluation",
    "migraton": "migration",
    "budegt": "budget",
    "desgin": "design",
    "incdient": "incident",
}

HYPHENATED: dict[str, tuple[str, ...]] = {
    "move-over": ("move", "over", "moveover"),
}


@dataclass(frozen=True)
class NormalizedQuery:
    raw: str
    terms: tuple[str, ...]
    cohorts: tuple[str, ...]


def normalize_query(query: str) -> NormalizedQuery:
    """Expand only E002's explicit lexical surface-form rules while preserving evidence."""
    lowered = query.lower().strip()
    cohorts: set[str] = set()

    # Join dotted initials before generic punctuation tokenization: O.H. -> oh.
    if re.search(r"\b(?:[a-z]\.){2,}", lowered):
        lowered = re.sub(r"\b((?:[a-z]\.){2,})", lambda m: m.group(1).replace(".", ""), lowered)
        cohorts.add("initials")

    expanded_text = lowered
    for form, additions in HYPHENATED.items():
        if form in expanded_text:
            expanded_text += " " + " ".join(additions)
            cohorts.add("hyphenation")

    base_terms = re.findall(r"[a-z0-9]+", expanded_text)
    terms = list(base_terms)

    for term in base_terms:
        canonical = MISSPELLINGS.get(term)
        if canonical:
            terms.append(canonical)
            cohorts.add("misspelling")
        alias_terms = ALIASES.get(term)
        if alias_terms:
            terms.extend(alias_terms)
            cohorts.add("alias")

    # Preserve order while avoiding accidental duplicate weighting.
    unique_terms = tuple(dict.fromkeys(terms))
    return NormalizedQuery(raw=query, terms=unique_terms, cohorts=tuple(sorted(cohorts)) or ("none",))
