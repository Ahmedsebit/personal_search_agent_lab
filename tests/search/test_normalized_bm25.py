from datetime import datetime, timezone

from packages.search.models import Email
from packages.search.retrieval.bm25 import BM25Retriever
from packages.search.retrieval.normalized_bm25 import QueryNormalizedBM25Retriever


def _email(document_id: str, sender: str, subject: str, body: str = "") -> Email:
    return Email(document_id, "u", sender, ("Bob",), subject, body, datetime.now(timezone.utc))


def test_e002_alias_can_recover_candidate_e001_misses():
    documents = [_email("1", "Daniel Kim", "budget review"), _email("2", "Alice", "budget review")]
    e001 = BM25Retriever(); e001.index(documents)
    e002 = QueryNormalizedBM25Retriever(); e002.index(documents)
    assert "1" not in [result.document_id for result in e001.search("budget from Dan", k=1)]
    assert e002.search("budget from Dan", k=1)[0].document_id == "1"
    assert "alias" in e002.last_normalization.cohorts


def test_e002_initials_are_normalized_without_changing_e001():
    documents = [_email("1", "Omar Hassan", "architecture"), _email("2", "Alice", "architecture")]
    e002 = QueryNormalizedBM25Retriever(); e002.index(documents)
    assert e002.search("architecture from O.H.", k=1)[0].document_id == "1"
    assert {"initials", "alias"} <= set(e002.last_normalization.cohorts)


def test_e002_misspelling_can_recover_canonical_term():
    documents = [_email("1", "Alice", "ranking experiment"), _email("2", "Alice", "experiment")]
    e002 = QueryNormalizedBM25Retriever(); e002.index(documents)
    assert e002.search("rankng experiment", k=1)[0].document_id == "1"
    assert "misspelling" in e002.last_normalization.cohorts


def test_e002_hyphenation_records_cohort_and_searches_expanded_terms():
    documents = [_email("1", "Alice", "move over migration"), _email("2", "Alice", "unrelated")]
    e002 = QueryNormalizedBM25Retriever(); e002.index(documents)
    assert e002.search("move-over", k=1)[0].document_id == "1"
    assert "hyphenation" in e002.last_normalization.cohorts


def test_e002_none_cohort_preserves_e001_ranking():
    documents = [_email("1", "Alice", "Atlas ranking", "ranking ranking"), _email("2", "Alice", "Atlas update")]
    e001 = BM25Retriever(); e001.index(documents)
    e002 = QueryNormalizedBM25Retriever(); e002.index(documents)
    baseline = [(r.document_id, r.score) for r in e001.search("Atlas ranking", k=2)]
    treatment = [(r.document_id, r.score) for r in e002.search("Atlas ranking", k=2)]
    assert treatment == baseline
    assert e002.last_normalization.cohorts == ("none",)


def test_e002_result_source_is_distinct():
    retriever = QueryNormalizedBM25Retriever(); retriever.index([_email("1", "Daniel Kim", "budget")])
    assert retriever.search("Dan budget", k=1)[0].source == "query-normalized-bm25"
