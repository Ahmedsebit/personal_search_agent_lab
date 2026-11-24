"""Small frozen-style BM25 implementation used by the standalone E002b package.

The original project repository is unavailable in this environment. This module
provides a compatible learning/test double so E002b retriever integration can be
executed and validated. In the original repository, ContextAwareBM25Retriever
should wrap the existing frozen E001 BM25Retriever instead.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
import re
from typing import Iterable, Mapping, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    score: float


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(text.lower()))


class BM25Retriever:
    def __init__(
        self,
        documents: Mapping[str, str],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.document_ids = tuple(sorted(documents))
        self.term_frequencies: dict[str, Counter[str]] = {}
        self.document_lengths: dict[str, int] = {}
        self.document_frequency: Counter[str] = Counter()
        self.postings: dict[str, set[str]] = defaultdict(set)

        for document_id in self.document_ids:
            terms = tokenize(documents[document_id])
            frequencies = Counter(terms)
            self.term_frequencies[document_id] = frequencies
            self.document_lengths[document_id] = len(terms)
            for term in frequencies:
                self.document_frequency[term] += 1
                self.postings[term].add(document_id)

        self.document_count = len(self.document_ids)
        self.average_document_length = (
            sum(self.document_lengths.values()) / self.document_count
            if self.document_count
            else 0.0
        )

    def search_terms(self, query_terms: Sequence[str], k: int = 50) -> list[SearchHit]:
        if k <= 0 or not self.document_count:
            return []

        unique_terms = tuple(dict.fromkeys(term.lower() for term in query_terms))
        candidates: set[str] = set()
        for term in unique_terms:
            candidates.update(self.postings.get(term, ()))

        scored = [
            SearchHit(document_id=document_id, score=self._score(document_id, unique_terms))
            for document_id in candidates
        ]
        scored.sort(key=lambda hit: (-hit.score, hit.document_id))
        return scored[:k]

    def search(self, query: str, k: int = 50) -> list[SearchHit]:
        return self.search_terms(tokenize(query), k=k)

    def _score(self, document_id: str, query_terms: Iterable[str]) -> float:
        score = 0.0
        frequencies = self.term_frequencies[document_id]
        document_length = self.document_lengths[document_id]

        for term in query_terms:
            term_frequency = frequencies.get(term, 0)
            if not term_frequency:
                continue
            document_frequency = self.document_frequency[term]
            inverse_document_frequency = math.log(
                1
                + (
                    self.document_count - document_frequency + 0.5
                )
                / (document_frequency + 0.5)
            )
            length_ratio = (
                document_length / self.average_document_length
                if self.average_document_length
                else 0.0
            )
            denominator = term_frequency + self.k1 * (
                1 - self.b + self.b * length_ratio
            )
            term_component = term_frequency * (self.k1 + 1) / denominator
            score += inverse_document_frequency * term_component

        return score
