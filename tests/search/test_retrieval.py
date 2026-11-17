from datetime import datetime, timezone
from packages.search.models import Email
from packages.search.retrieval.bm25 import BM25Retriever
from packages.search.retrieval.dense import HashingDenseRetriever
from packages.search.retrieval.hybrid import ReciprocalRankFusionRetriever


def corpus():
    now = datetime.now(timezone.utc)
    return [
        Email("1", "u", "Alice", ("Bob",), "Atlas authentication", "final design decision", now),
        Email("2", "u", "Omar", ("Bob",), "Falcon budget", "quarterly cost review", now),
    ]


def test_bm25_finds_exact_match():
    retriever = BM25Retriever(); retriever.index(corpus())
    assert retriever.search("Atlas authentication", 1)[0].document_id == "1"


def test_dense_and_hybrid_return_results():
    bm25 = BM25Retriever(); dense = HashingDenseRetriever(64)
    hybrid = ReciprocalRankFusionRetriever([bm25, dense]); hybrid.index(corpus())
    assert hybrid.search("Atlas design", 2)
