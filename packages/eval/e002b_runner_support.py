"""Runner registration and result serialization support for E002b."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict
from typing import Any

from packages.search.query.context_aware_normalization import ContextAwareQueryNormalizer
from packages.search.retrieval.context_aware_bm25 import (
    ContextAwareBM25Retriever,
    RetrievalResult,
)

RETRIEVER_TYPE = "context_aware_normalized_bm25"


def build_e002b_retriever(
    documents: Mapping[str, str],
    config: Mapping[str, Any],
    *,
    aliases: Mapping[str, tuple[str, ...]],
    known_full_names: tuple[tuple[str, ...], ...],
    misspellings: Mapping[str, str] | None = None,
    hyphenations: Mapping[str, tuple[str, ...]] | None = None,
) -> ContextAwareBM25Retriever:
    retrieval = config.get("retrieval", {})
    bm25_config = retrieval.get("bm25", {})
    normalizer = ContextAwareQueryNormalizer(
        aliases=aliases,
        known_full_names=known_full_names,
        misspellings=misspellings,
        hyphenations=hyphenations,
    )

    # ContextAwareBM25Retriever imports the original E001 BM25 through the
    # adapter when executed inside the full repository.
    from packages.search.retrieval.e001_adapter import BM25Retriever

    bm25 = BM25Retriever(
        documents,
        k1=float(bm25_config.get("k1", 1.5)),
        b=float(bm25_config.get("b", 0.75)),
    )
    return ContextAwareBM25Retriever(
        documents,
        normalizer=normalizer,
        bm25=bm25,
    )


def register_e002b_retriever(
    registry: dict[str, Callable[..., object]],
) -> None:
    registry[RETRIEVER_TYPE] = build_e002b_retriever


def e002b_query_metadata(result: RetrievalResult) -> dict[str, object]:
    normalized = result.normalized_query
    return {
        "source": result.source,
        "normalized_terms": list(normalized.terms),
        "cohorts": list(normalized.cohorts),
        "suppressed_aliases": [asdict(item) for item in normalized.suppressed_aliases],
    }
