from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Sequence

from packages.search.indexing.indexer import document_frequency, tokenize
from packages.search.models import Email, SearchResult


def inverse_document_frequency(document_count: int, document_frequency: int) -> float:
    """Return the positive BM25 IDF for one term."""
    if document_count <= 0:
        return 0.0
    if document_frequency < 0 or document_frequency > document_count:
        raise ValueError("document_frequency must be between 0 and document_count")
    return math.log(
        1.0 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
    )


def term_frequency_component(
    term_frequency: int,
    document_length: int,
    average_document_length: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Return BM25's saturated TF and document-length-normalization component."""
    if term_frequency <= 0:
        return 0.0
    if document_length < 0:
        raise ValueError("document_length cannot be negative")
    if average_document_length <= 0:
        raise ValueError("average_document_length must be positive")
    if k1 < 0:
        raise ValueError("k1 cannot be negative")
    if not 0.0 <= b <= 1.0:
        raise ValueError("b must be between 0 and 1")

    length_factor = 1.0 - b + b * document_length / average_document_length
    denominator = term_frequency + k1 * length_factor
    return term_frequency * (k1 + 1.0) / denominator


def bm25_term_score(
    term_frequency: int,
    document_frequency: int,
    document_length: int,
    document_count: int,
    average_document_length: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Return one query term's contribution to a document's BM25 score."""
    if term_frequency <= 0:
        return 0.0
    return inverse_document_frequency(document_count, document_frequency) * term_frequency_component(
        term_frequency,
        document_length,
        average_document_length,
        k1,
        b,
    )


class BM25Retriever:
    """In-memory BM25 retriever used as the frozen E001 lexical baseline."""

    name = "bm25"

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        if k1 < 0:
            raise ValueError("k1 cannot be negative")
        if not 0.0 <= b <= 1.0:
            raise ValueError("b must be between 0 and 1")
        self.k1 = k1
        self.b = b
        self._documents: list[Email] = []
        self._term_frequencies: list[Counter[str]] = []
        self._document_frequency: Counter[str] = Counter()
        self._postings: dict[str, set[int]] = {}
        self._lengths: list[int] = []
        self._average_length = 0.0

    def index(self, documents: Sequence[Email]) -> None:
        self._documents = list(documents)
        tokenized = [tokenize(document.searchable_text) for document in self._documents]
        self._term_frequencies = [Counter(tokens) for tokens in tokenized]
        self._document_frequency = document_frequency(tokenized)
        self._lengths = [len(tokens) for tokens in tokenized]
        self._average_length = sum(self._lengths) / len(self._lengths) if self._lengths else 0.0

        postings: defaultdict[str, set[int]] = defaultdict(set)
        for document_index, frequencies in enumerate(self._term_frequencies):
            for term in frequencies:
                postings[term].add(document_index)
        self._postings = dict(postings)

    def search(self, query: str, k: int = 50, *, limit: int | None = None) -> list[SearchResult]:
        """Return the top-k BM25 matches.

        ``k`` defaults to 50 for the E001 benchmark. ``limit`` is retained as a
        keyword-only compatibility alias for the shared Retriever interface.
        """
        if limit is not None:
            k = limit
        if k <= 0 or not self._documents:
            return []

        # E001 treats repeated query terms once; query term-frequency weighting is out of scope.
        query_terms = set(tokenize(query))
        candidate_indexes: set[int] = set()
        for term in query_terms:
            candidate_indexes.update(self._postings.get(term, set()))

        document_count = len(self._documents)
        scored: list[tuple[str, float]] = []
        for index in candidate_indexes:
            frequencies = self._term_frequencies[index]
            length = self._lengths[index]
            score = sum(
                bm25_term_score(
                    term_frequency=frequencies.get(term, 0),
                    document_frequency=self._document_frequency.get(term, 0),
                    document_length=length,
                    document_count=document_count,
                    average_document_length=self._average_length,
                    k1=self.k1,
                    b=self.b,
                )
                for term in query_terms
            )
            if score > 0:
                scored.append((self._documents[index].id, score))

        # Stable document-ID tie-breaking makes repeated runs reproducible.
        scored.sort(key=lambda item: (-item[1], item[0]))
        return [
            SearchResult(document_id=document_id, score=score, rank=rank, source=self.name)
            for rank, (document_id, score) in enumerate(scored[:k], start=1)
        ]
