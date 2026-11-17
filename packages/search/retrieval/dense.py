from __future__ import annotations

import hashlib
import math
from typing import Sequence

from packages.search.indexing.indexer import tokenize
from packages.search.models import Email, SearchResult


class HashingDenseRetriever:
    """Dependency-light dense baseline using deterministic feature hashing."""

    name = "dense_hashing"

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions
        self._documents: list[Email] = []
        self._vectors: list[list[float]] = []

    def _vectorize(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = tokenize(text)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for feature in features:
            digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            index = number % self.dimensions
            sign = 1.0 if number & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def index(self, documents: Sequence[Email]) -> None:
        self._documents = list(documents)
        self._vectors = [self._vectorize(document.searchable_text) for document in self._documents]

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        query_vector = self._vectorize(query)
        scored = []
        for document, vector in zip(self._documents, self._vectors):
            score = sum(a * b for a, b in zip(query_vector, vector))
            if score > 0:
                scored.append((document.id, score))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return [
            SearchResult(document_id=document_id, score=score, rank=rank, source=self.name)
            for rank, (document_id, score) in enumerate(scored[:limit], start=1)
        ]
