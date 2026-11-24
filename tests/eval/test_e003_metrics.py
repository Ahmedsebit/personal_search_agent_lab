import csv, math, os
from packages.eval.e003_metrics import compute_metrics, control_parity

ANN = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "experiments", "e003", "e003-query-annotations.csv")


def test_basic_metrics():
    m = compute_metrics(["x", "a", "b"], {"a": 1, "b": 1, "c": 1})
    assert math.isclose(m["mrr"], 0.5) and math.isclose(m["recall@50"], 2 / 3) and math.isclose(m["precision@10"], 0.2)


def test_perfect_ranking_ndcg_one_both_modes():
    for mode in ("linear", "exponential"):
        assert math.isclose(compute_metrics(["a", "b"], {"a": 2, "b": 1}, mode)["ndcg@10"], 1.0)


def test_control_parity_detects_mismatch():
    ann = list(csv.DictReader(open(ANN)))[:1]
    pq = [{"query_id": ann[0]["query_id"], "metrics": {m: float(ann[0]["control_" + m.replace("@", "_at_")])
           for m in ("ndcg@10", "recall@50", "mrr", "precision@10", "recall@10", "dcg@10")}}]
    assert control_parity(pq, ann)["pass"]
    pq[0]["metrics"]["ndcg@10"] += 0.1
    assert not control_parity(pq, ann)["pass"]
