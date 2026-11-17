from __future__ import annotations

import math
from collections import Counter
from typing import Sequence

from packages.search.indexing.indexer import document_frequency, term_frequencies, tokenize
from packages.search.models import Email, SearchResult


class BM25Retriever:
    name = "bm25"

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._documents: list[Email] = []
        self._term_frequencies: list[Counter[str]] = []
        self._document_frequency: Counter[str] = Counter()
        self._lengths: list[int] = []
        self._average_length = 0.0

    def index(self, documents: Sequence[Email]) -> None:
        self._documents = list(documents)
        tokenized = [tokenize(document.searchable_text) for document in self._documents]
        self._term_frequencies = [Counter(tokens) for tokens in tokenized]
        self._document_frequency = document_frequency(tokenized)
        self._lengths = [len(tokens) for tokens in tokenized]
        self._average_length = sum(self._lengths) / max(len(self._lengths), 1)

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        query_terms = tokenize(query)
        scored: list[tuple[str, float]] = []
        document_count = len(self._documents)
        for index, document in enumerate(self._documents):
            score = 0.0
            frequencies = self._term_frequencies[index]
            length = self._lengths[index]
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                df = self._document_frequency.get(term, 0)
                idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
                normalizer = frequency + self.k1 * (
                    1 - self.b + self.b * length / max(self._average_length, 1.0)
                )
                score += idf * frequency * (self.k1 + 1) / normalizer
            if score > 0:
                scored.append((document.id, score))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return [
            SearchResult(document_id=document_id, score=score, rank=rank, source=self.name)
            for rank, (document_id, score) in enumerate(scored[:limit], start=1)
        ]
