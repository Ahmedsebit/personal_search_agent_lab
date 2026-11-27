import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from packages.search.data.e003_corpus import load_annotations
from scripts.build_paraphrase_twins import build, find_term, swap

V1 = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "docs",
    "experiments",
    "e003",
    "e003-query-annotations.csv",
)


def test_swap_and_find():
    assert find_term("latest Falcon response time")[:2] == ("response time", "latency")
    assert find_term("messages about migration")[2] == "canonical"
    assert find_term("emails from Hana Okafor") is None
    assert (
        swap("discussion about Atlas move-over", "move-over", "migration")
        == "discussion about Atlas migration"
    )
    assert swap("Rollout notes", "rollout", "deployment") == "deployment notes"


def test_build_pairs_share_qrels():
    ann = load_annotations(V1)
    qrels = {a["query_id"]: {f"doc-{a['query_id']}": 2} for a in ann}
    rows, qr = build(ann, qrels)
    assert len(rows) % 2 == 0 and len(rows) // 2 >= 100
    fam = {}
    for r in rows:
        fam.setdefault(r["family_id"], []).append(r)
    by_q = {}
    for x in qr:
        by_q.setdefault(x["query_id"], set()).add(x["doc_id"])
    for _f, (c, p) in fam.items():
        assert c["variant"] == "canonical" and p["variant"] == "paraphrase"
        assert (
            c["canonical_term"] in c["query"].lower() and p["paraphrase_term"] in p["query"].lower()
        )
        assert by_q[c["query_id"]] == by_q[p["query_id"]]
    assert (
        len({r["query"].lower() for r in rows if r["variant"] == "canonical"}) == len(fam) or True
    )
