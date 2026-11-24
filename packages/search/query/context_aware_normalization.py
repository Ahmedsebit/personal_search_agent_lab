"""E002b context-aware alias normalization.

This module implements the single approved E002b intervention: aliases are
expanded only when their token positions are not protected by a known full-name
span. It does not perform retrieval or modify BM25 scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_DOTTED_INITIALS_RE = re.compile(r"\b(?:[A-Za-z]\.){2,}")


@dataclass(frozen=True)
class SuppressedAlias:
    alias: str
    reason: str
    phrase: str
    token_index: int


@dataclass(frozen=True)
class NormalizedQuery:
    raw: str
    terms: tuple[str, ...]
    cohorts: tuple[str, ...]
    suppressed_aliases: tuple[SuppressedAlias, ...] = ()


def _stable_unique(values: Iterable[str]) -> tuple[str, ...]:
    """Return values in first-seen order without duplicates."""
    return tuple(dict.fromkeys(values))


def _normalize_dotted_initials(text: str) -> tuple[str, bool]:
    """Convert a dotted initial sequence such as O.H. to OH before tokenizing."""
    fired = False

    def replace(match: re.Match[str]) -> str:
        nonlocal fired
        fired = True
        return match.group(0).replace(".", "")

    return _DOTTED_INITIALS_RE.sub(replace, text), fired


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(text.lower()))


class ContextAwareQueryNormalizer:
    """Normalize E002 queries while suppressing unsafe alias expansion.

    Known names are matched longest-first. Every token position covered by a
    known full-name span is protected. An alias at a protected position is kept
    as literal evidence but its canonical expansion is suppressed.
    """

    def __init__(
        self,
        *,
        aliases: Mapping[str, Sequence[str]],
        known_full_names: Iterable[Sequence[str]],
        misspellings: Mapping[str, str] | None = None,
        hyphenations: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self.aliases = {
            alias.lower(): tuple(term.lower() for term in expansion)
            for alias, expansion in aliases.items()
        }
        normalized_names = {
            tuple(part.lower() for part in name)
            for name in known_full_names
            if len(tuple(name)) >= 2
        }
        self.known_full_names = tuple(
            sorted(normalized_names, key=lambda name: (-len(name), name))
        )
        self.misspellings = {
            source.lower(): target.lower()
            for source, target in (misspellings or {}).items()
        }
        self.hyphenations = {
            source.lower(): tuple(term.lower() for term in expansion)
            for source, expansion in (hyphenations or {}).items()
        }

    def normalize(self, raw: str) -> NormalizedQuery:
        initials_text, initials_fired = _normalize_dotted_initials(raw)
        tokens = _tokenize(initials_text)
        protected = self._protected_name_positions(tokens)

        terms: list[str] = list(tokens)
        cohorts: list[str] = []
        suppressed: list[SuppressedAlias] = []

        if initials_fired:
            cohorts.append("initials")

        for index, token in enumerate(tokens):
            if token in self.misspellings:
                terms.append(self.misspellings[token])
                cohorts.append("misspelling")

            if token in self.aliases:
                protected_phrase = protected.get(index)
                if protected_phrase is not None:
                    suppressed.append(
                        SuppressedAlias(
                            alias=token,
                            reason="explicit_full_name",
                            phrase=" ".join(protected_phrase),
                            token_index=index,
                        )
                    )
                    cohorts.append("alias_collision")
                else:
                    terms.extend(self.aliases[token])
                    cohorts.append("alias")

        lower_raw = raw.lower()
        for surface, additions in self.hyphenations.items():
            if surface in lower_raw:
                terms.extend(additions)
                cohorts.append("hyphenation")

        return NormalizedQuery(
            raw=raw,
            terms=_stable_unique(terms),
            cohorts=_stable_unique(cohorts),
            suppressed_aliases=tuple(suppressed),
        )

    def _protected_name_positions(
        self, tokens: Sequence[str]
    ) -> dict[int, tuple[str, ...]]:
        """Map protected positions to the longest matching known full name."""
        protected: dict[int, tuple[str, ...]] = {}
        occupied: set[int] = set()

        for name in self.known_full_names:
            width = len(name)
            for start in range(0, len(tokens) - width + 1):
                positions = range(start, start + width)
                if any(position in occupied for position in positions):
                    continue
                if tuple(tokens[start : start + width]) != name:
                    continue
                for position in positions:
                    protected[position] = name
                    occupied.add(position)

        return protected
