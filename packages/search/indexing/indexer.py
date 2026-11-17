from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def term_frequencies(text: str) -> Counter[str]:
    return Counter(tokenize(text))


def document_frequency(tokenized_documents: Iterable[list[str]]) -> Counter[str]:
    frequencies: Counter[str] = Counter()
    for tokens in tokenized_documents:
        frequencies.update(set(tokens))
    return frequencies
