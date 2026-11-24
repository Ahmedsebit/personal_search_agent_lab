import math
from collections import Counter
from packages.search.retrieval.field_aware_bm25 import FieldAwareBM25, lucene_idf
from packages.search.query.field_cues import default_tokenize as tok

DOCS = [
    {"doc_id": "a", "sender": "Fatima Ali", "subject": "Cedar rollout", "body": "rollout plan for cedar", "attachment_names": "", "recipients": ""},
    {"doc_id": "b", "sender": "Alice Morgan", "subject": "Ali asked", "body": "ali said rollout is late", "attachment_names": "", "recipients": "Fatima Ali"},
    {"doc_id": "c", "sender": "Leo Martin", "subject": "notes", "body": "cedar move over plan", "attachment_names": "cedar-move-over.xlsx", "recipients": ""},
    {"doc_id": "d", "sender": "Leo Martin", "subject": "notes", "body": "see body about cedar move over move over", "attachment_names": "", "recipients": ""},
]


def ref_bm25(docs, q, k1=1.2, b=0.75):
    toks = {d["doc_id"]: tok(d["body"]) for d in docs}
    avg = sum(map(len, toks.values())) / len(toks)
    out = {}
    for did, t in toks.items():
        c, s = Counter(t), 0.0
        for term in q:
            df = sum(term in x for x in toks.values())
            if c[term]:
                s += lucene_idf(len(docs), df) * c[term] * (k1 + 1) / (c[term] + k1 * (1 - b + b * len(t) / avg))
        if s:
            out[did] = s
    return out


def test_single_field_reduces_to_bm25():
    idx = FieldAwareBM25([{"doc_id": d["doc_id"], "body": d["body"]} for d in DOCS], fields=("body",))
    q = tok("cedar rollout plan")
    got = idx.score_plan([(t, {"body": 1.0}) for t in q])
    ref = ref_bm25(DOCS, q)
    assert set(got) == set(ref) and all(math.isclose(got[k], ref[k], rel_tol=1e-12) for k in ref)


def test_sender_routing_prefers_true_sender():
    idx = FieldAwareBM25(DOCS)
    sender_only = {"sender": 3.0}
    r = idx.search_plan([("fatima", sender_only), ("ali", sender_only)], 10)
    assert [d for d, _ in r] == ["a"]


def test_attachment_routing_promotes_attachment_doc():
    idx = FieldAwareBM25(DOCS)
    att = {"attachment_names": 4.0, "subject": 2.0, "body": 1.0}
    body = {"body": 1.0}
    q = tok("cedar move over")
    assert idx.search_plan([(t, body) for t in q], 1)[0][0] == "d"
    assert idx.search_plan([(t, att) for t in q], 1)[0][0] == "c"


def test_zero_weight_fields_ignored_and_deterministic_ties():
    idx = FieldAwareBM25([{"doc_id": "x", "body": "z"}, {"doc_id": "w", "body": "z"}], fields=("body",))
    assert idx.search_plan([("z", {"body": 0.0})]) == []
    assert [d for d, _ in idx.search_plan([("z", {"body": 1.0})])] == ["w", "x"]
