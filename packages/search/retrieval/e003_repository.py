"""Bind the E003+ harness to this repository's frozen E002b implementation."""

from __future__ import annotations

import re
from typing import Any

from packages.eval.e002b_runner_support import build_e002b_retriever
from packages.search.data.e003_corpus import resolve_fields, to_field_documents
from packages.search.indexing.indexer import tokenize
from packages.search.query.normalization import ALIASES, HYPHENATED, MISSPELLINGS
from packages.search.retrieval.context_aware_bm25 import ContextAwareBM25Retriever


def build_control(records: list[dict[str, Any]]) -> ContextAwareBM25Retriever:
    documents = to_field_documents(records, resolve_fields(records))
    identities = {
        tuple(tokenize(name))
        for doc in documents
        for name in (doc["sender"], *re.split(r"[;,]", doc["recipients"]))
        if name.strip()
    }
    return build_e002b_retriever(
        {
            doc["doc_id"]: " ".join(
                doc[field]
                for field in ("sender", "recipients", "subject", "body", "attachment_names")
            )
            for doc in documents
        },
        {"retrieval": {"bm25": {"k1": 1.5, "b": 0.75}}},
        aliases=ALIASES,
        known_full_names=tuple(sorted(identities)),
        misspellings=MISSPELLINGS,
        hyphenations=HYPHENATED,
    )
