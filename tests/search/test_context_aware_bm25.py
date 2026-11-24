from datetime import UTC, datetime

import pytest

from packages.search.models import Email
from packages.search.query.context_aware_normalization import ContextAwareQueryNormalizer
from packages.search.retrieval.bm25 import BM25Retriever as E001BM25Retriever
from packages.search.retrieval.context_aware_bm25 import ContextAwareBM25Retriever
from packages.search.retrieval.e001_adapter import BM25Retriever as E001BM25Adapter
from packages.search.retrieval.simple_bm25 import BM25Retriever


def make_components():
    documents = {
        "alice-1": "Alice Morgan sent the budget proposal",
        "fatima-1": "Fatima Ali sent the rollout plan",
        "fatima-2": "Rollout status from Fatima Ali",
        "omar-1": "Architecture review from Omar Hassan",
        "other-1": "Latest Atlas ranking experiment",
    }
    normalizer = ContextAwareQueryNormalizer(
        aliases={
            "ali": ("alice", "morgan"),
            "oh": ("omar", "hassan", "hussein"),
        },
        known_full_names={
            ("alice", "morgan"),
            ("fatima", "ali"),
            ("omar", "hassan"),
        },
    )
    return documents, normalizer


def test_separate_retriever_exposes_e002b_source_and_metadata() -> None:
    documents, normalizer = make_components()
    retriever = ContextAwareBM25Retriever(documents, normalizer=normalizer)

    result = retriever.search("emails from Fatima Ali")

    assert result.source == "context-aware-query-normalized-bm25"
    assert "alias_collision" in result.normalized_query.cohorts
    assert result.normalized_query.suppressed_aliases[0].phrase == "fatima ali"


def test_collision_query_does_not_retrieve_alice_from_added_alias_terms() -> None:
    documents, normalizer = make_components()
    retriever = ContextAwareBM25Retriever(documents, normalizer=normalizer)

    result = retriever.search("rollout from Fatima Ali", k=5)
    ids = [hit.document_id for hit in result.hits]

    assert ids[:2] == ["fatima-2", "fatima-1"]
    assert "alice-1" not in ids


def test_safe_standalone_alias_retains_expansion() -> None:
    documents, normalizer = make_components()
    retriever = ContextAwareBM25Retriever(documents, normalizer=normalizer)

    result = retriever.search("emails from Ali", k=5)

    assert {"alice", "morgan"}.issubset(result.normalized_query.terms)
    assert result.hits[0].document_id == "alice-1"


def test_initials_still_retrieve_canonical_name() -> None:
    documents, normalizer = make_components()
    retriever = ContextAwareBM25Retriever(documents, normalizer=normalizer)

    result = retriever.search("architecture from O.H.", k=5)

    assert result.hits[0].document_id == "omar-1"
    assert {"initials", "alias"}.issubset(result.normalized_query.cohorts)


def test_none_query_matches_frozen_bm25_ranking() -> None:
    documents, normalizer = make_components()
    baseline = BM25Retriever(documents)
    retriever = ContextAwareBM25Retriever(
        documents,
        normalizer=normalizer,
        bm25=baseline,
    )

    expected = baseline.search("latest Atlas ranking", k=5)
    actual = retriever.search("latest Atlas ranking", k=5)

    assert actual.normalized_query.cohorts == ()
    assert actual.hits == tuple(expected)


def test_top_k_is_preserved() -> None:
    documents, normalizer = make_components()
    retriever = ContextAwareBM25Retriever(documents, normalizer=normalizer)

    result = retriever.search("Fatima rollout", k=1)

    assert len(result.hits) == 1


@pytest.mark.parametrize(("k1", "b"), [(1.5, 0.75), (0.4, 0.2), (0.0, 0.0)])
def test_adapter_preserves_e001_scores_and_ranking(k1: float, b: float) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    emails = [
        Email("b", "u", "Alice", (), "Budget", "budget proposal", now),
        Email("a", "u", "Alice", (), "Budget", "budget proposal", now),
        Email("c", "u", "Fatima", (), "Rollout", "plan", now),
    ]
    baseline = E001BM25Retriever(k1=k1, b=b)
    baseline.index(emails)
    adapter = E001BM25Adapter({email.id: email.searchable_text for email in emails}, k1=k1, b=b)
    for query, k in [
        ("budget Alice budget", 2),
        ("rollout", 1),
        ("unknown", 5),
        ("", 5),
        ("budget", 0),
    ]:
        expected = baseline.search(query, k=k)
        actual = adapter.search_terms(query.split(), k=k)

        assert [hit.document_id for hit in actual] == [hit.document_id for hit in expected]
        assert [hit.score for hit in actual] == pytest.approx([hit.score for hit in expected])


def test_adapter_accepts_empty_corpus() -> None:
    assert E001BM25Adapter({}).search_terms(("budget",)) == []
