import pytest

from packages.search.retrieval.bm25 import bm25_term_score, term_frequency_component


BASE = dict(document_length=100, document_count=2000, average_document_length=100.0)


def test_rare_terms_score_higher_than_common_terms():
    rare = bm25_term_score(term_frequency=2, document_frequency=10, **BASE)
    common = bm25_term_score(term_frequency=2, document_frequency=1000, **BASE)
    assert rare > common


def test_repetition_helps_with_diminishing_returns():
    scores = [
        bm25_term_score(term_frequency=tf, document_frequency=100, **BASE)
        for tf in (1, 2, 3)
    ]
    assert scores[0] < scores[1] < scores[2]
    assert scores[1] - scores[0] > scores[2] - scores[1]


def test_longer_documents_receive_a_smaller_component():
    short = term_frequency_component(2, 50, 100.0)
    long = term_frequency_component(2, 200, 100.0)
    assert short > long


def test_b_zero_disables_length_normalization():
    short = term_frequency_component(2, 50, 100.0, b=0.0)
    long = term_frequency_component(2, 200, 100.0, b=0.0)
    assert short == pytest.approx(long)


def test_larger_k1_allows_repetition_to_matter_longer():
    low_k1_gap = term_frequency_component(10, 100, 100.0, k1=0.5) - term_frequency_component(
        1, 100, 100.0, k1=0.5
    )
    high_k1_gap = term_frequency_component(10, 100, 100.0, k1=3.0) - term_frequency_component(
        1, 100, 100.0, k1=3.0
    )
    assert high_k1_gap > low_k1_gap


def test_absent_term_contributes_zero():
    assert bm25_term_score(term_frequency=0, document_frequency=10, **BASE) == 0.0

from datetime import datetime, timezone
from packages.search.models import Email
from packages.search.retrieval.bm25 import BM25Retriever


def _search_corpus(count: int = 80):
    now = datetime.now(timezone.utc)
    return [
        Email(
            id=f"doc-{i:03d}",
            owner_id="u",
            sender="Alice",
            recipients=("Bob",),
            subject=f"ranking experiment {i}",
            body="ranking ranking evaluation" if i % 2 == 0 else "ranking evaluation",
            sent_at=now,
        )
        for i in range(count)
    ]


def test_search_defaults_to_top_50():
    retriever = BM25Retriever()
    retriever.index(_search_corpus())
    results = retriever.search("ranking")
    assert len(results) == 50
    assert [result.rank for result in results] == list(range(1, 51))


def test_search_accepts_explicit_k():
    retriever = BM25Retriever()
    retriever.index(_search_corpus())
    assert len(retriever.search("ranking", k=7)) == 7


def test_search_returns_scores_in_descending_order():
    retriever = BM25Retriever()
    retriever.index(_search_corpus())
    scores = [result.score for result in retriever.search("ranking", k=20)]
    assert scores == sorted(scores, reverse=True)


def test_search_no_match_returns_empty_list():
    retriever = BM25Retriever()
    retriever.index(_search_corpus())
    assert retriever.search("doesnotexist") == []
