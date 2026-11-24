import numpy as np
import pytest

from packages.search.pipeline.builder import make_encoder
from packages.search.pipeline.stages import (
    FilterStage,
    FunctionStage,
    HybridRRFStage,
    QueryRewriteStage,
    RerankStage,
    rrf_fuse,
)
from packages.search.retrieval.semantic_dense import DenseRetriever, HashingEncoder, document_text

DOCS = [
    {
        "doc_id": f"d{i}",
        "sender": "Leo",
        "subject": s,
        "body": b,
        "attachment_names": "",
        "recipients": "",
    }
    for i, (s, b) in enumerate(
        [
            ("budget", "q3 budget numbers"),
            ("spend plan", "spend plan draft"),
            ("latency", "p95 latency"),
            ("misc", "lunch"),
        ]
    )
]


def lex(q, k):
    words = set(q.lower().split())
    hits = [(d["doc_id"], float(len(words & set(document_text(d).lower().split())))) for d in DOCS]
    return sorted([h for h in hits if h[1] > 0], key=lambda x: (-x[1], x[0]))[:k]


def test_rewrite_stage_passes_through_unchanged():
    s = QueryRewriteStage(FunctionStage(lex), lambda q: (q, {}), name="syn")
    r, m = s.search("budget", 10)
    assert r == lex("budget", 10) and m["syn"]["changed"] is False


def test_filter_stage_bypass_and_filter():
    s = FilterStage(
        FunctionStage(lex),
        lambda q: (
            q.replace(" yesterday", ""),
            (lambda d: d == "d1") if "yesterday" in q else None,
            {},
        ),
    )
    assert s.search("spend plan", 10)[0] == lex("spend plan", 10)
    assert [d for d, _ in s.search("spend plan yesterday", 10)[0]] == ["d1"]


def test_rrf():
    fused = rrf_fuse([[("a", 9), ("b", 8)], [("b", 1), ("c", 0.5)]], k=60)
    assert fused[0][0] == "b" and {d for d, _ in fused} == {"a", "b", "c"}


def test_hybrid_and_dense():
    dense = DenseRetriever(DOCS, HashingEncoder())
    r, _ = dense.search("spend plan", 2)
    assert r[0][0] == "d1"
    h = HybridRRFStage([FunctionStage(lex), dense], k=60, depth=4)
    assert h.search("budget", 3)[0][0][0] == "d0"


def test_rerank_preserves_set_and_tail():
    base = FunctionStage(lambda q, k: [("d3", 3.0), ("d2", 2.0), ("d1", 1.0), ("d0", 0.5)][:k])
    rr = RerankStage(
        base, lambda q, ids: [{"d3": 0, "d2": 5, "d1": 1, "d0": 9}[i] for i in ids], depth=3
    )
    r, _ = rr.search("x", 4)
    assert [d for d, _ in r][:3] == ["d2", "d1", "d3"] and r[3][0] == "d0"


def test_dense_cache_roundtrip(tmp_path):
    p = str(tmp_path / "emb.npy")
    a = DenseRetriever(DOCS, HashingEncoder(), p)
    b = DenseRetriever(DOCS, HashingEncoder(), p)
    assert np.allclose(a.emb, b.emb)


def test_dense_cache_invalidates_for_changed_corpus(tmp_path):
    path = str(tmp_path / "emb.npy")
    DenseRetriever(DOCS, HashingEncoder(), path)
    changed = [dict(doc, body="replacement text", subject="replacement") for doc in DOCS]
    cached = DenseRetriever(changed, HashingEncoder(), path)
    fresh = DenseRetriever(changed, HashingEncoder())
    assert np.allclose(cached.emb, fresh.emb)


def test_dense_ties_use_document_ids_at_the_top_k_boundary():
    dense = DenseRetriever(list(reversed(DOCS)), HashingEncoder())
    assert dense.search("", 1)[0][0][0] == "d0"
    assert dense.search("", 0)[0] == []
    assert DenseRetriever([], HashingEncoder()).search("budget", 10)[0] == []


def test_rerank_rejects_missing_scores():
    stage = RerankStage(FunctionStage(lex), lambda query, ids: [], depth=2)
    with pytest.raises(ValueError):
        stage.search("budget", 2)


def test_pipeline_test_encoders_require_smoke_mode(monkeypatch):
    monkeypatch.delenv("E003_SMOKE", raising=False)
    with pytest.raises(ValueError, match="E003_SMOKE=1"):
        make_encoder("hashing")
