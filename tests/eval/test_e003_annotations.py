import csv, hashlib, os
from collections import Counter

ANN = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "experiments", "e003", "e003-query-annotations.csv")
FROZEN = "ca0acd5db4dbed7a232f88ed664bce4cb9a5e5e6fb9cc7f26e3e29f5daff6d49"


def rows():
    return list(csv.DictReader(open(ANN)))


def test_hash_frozen():
    assert hashlib.sha256(open(ANN, "rb").read()).hexdigest() == FROZEN


def test_preregistered_cohort_sizes():
    r = rows()
    c = Counter(x["e003_cohort"] for x in r)
    assert len(r) == 200 and c == {"field_only": 75, "temporal_only": 25, "field_and_temporal": 25, "neither": 75}
    assert sum(x["sub_f_ordering"] == "1" for x in r) == 20
    assert sum(x["sub_t_ordering"] == "1" for x in r) == 13
    assert sum(x["sub_paraphrase_recall_limited"] == "1" for x in r) == 60
    assert {x["query_id"] for x in r if x["e002b_diagnostic"] == "1"} == {"query-0056", "query-0186"}
