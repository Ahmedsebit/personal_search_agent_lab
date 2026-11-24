from packages.search.query.synonym_expansion import LEXICON, expand


def test_paraphrase_appends_canonical():
    q, info = expand("messages about spend plan")
    assert q == "messages about spend plan budget" and info["expansions"] == [
        {"matched": "spend plan", "added": "budget"}
    ]


def test_bidirectional_canonical_appends_paraphrase():
    assert expand("messages about latency")[0] == "messages about latency response time"
    assert expand("messages about latency", bidirectional=False)[0] == "messages about latency"


def test_hyphenated_and_overlap_safe():
    assert expand("latest Atlas move-over")[0] == "latest Atlas move-over migration"
    q, info = expand("sign-in security review")
    assert len(info["expansions"]) == 1 and q.endswith("authentication")


def test_unrelated_query_untouched():
    for q in ("emails from Hana Okafor", "decision on OrionX", "atlassian deployment"[:9]):
        assert expand(q)[0] == q


def test_word_boundaries():
    assert expand("rollouts")[0] == "rollouts"


def test_replace_mode():
    assert (
        expand("rollout from Fatima Ali", bidirectional=False, mode="replace")[0]
        == "deployment from Fatima Ali"
    )


def test_lexicon_is_frozen_ten_pairs():
    assert len(LEXICON) == 10 and len(set(LEXICON.values())) == 10
