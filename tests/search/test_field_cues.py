from packages.search.query.field_cues import build_query_plan, SENDER_SPAN_WEIGHTS, ATTACHMENT_TOPIC_WEIGHTS, DEFAULT_FIELD_WEIGHTS


def terms(plan):
    return [t for t, _ in plan.terms]


def test_sender_span_routed_to_sender_only():
    p = build_query_plan("rollout from Fatima Ali")
    assert p.cues == ["sender"] and p.sender_span == ["fatima", "ali"]
    assert dict(p.terms)["fatima"] == SENDER_SPAN_WEIGHTS
    assert dict(p.terms)["rollout"] == DEFAULT_FIELD_WEIGHTS
    assert "from" not in terms(p)


def test_e002b_expanded_span_all_sender():
    # E002b output for 'emails from Ali' carries alias expansions in the span
    p = build_query_plan("emails from ali alice morgan")
    assert terms(p) == ["ali", "alice", "morgan"]
    assert all(w == SENDER_SPAN_WEIGHTS for _, w in p.terms)


def test_attachment_topic_routing():
    p = build_query_plan("attachment about Cedar move-over")
    assert p.cues == ["attachment"] and terms(p) == ["cedar", "move", "over"]
    assert all(w == ATTACHMENT_TOPIC_WEIGHTS for _, w in p.terms)


def test_mixed_query_keeps_head_terms_and_sender():
    p = build_query_plan("latest decision about Falcon rollout from Ally")
    assert p.cues == ["sender"]
    assert "about" not in terms(p) and "latest" in terms(p) and p.sender_span == ["ally"]


def test_no_cue_keeps_all_tokens():
    p = build_query_plan("discussion about Cedar migration")
    assert p.cues == [] and terms(p) == ["discussion", "about", "cedar", "migration"]


def test_routing_off_ablation():
    p = build_query_plan("rollout from Fatima Ali", routing=False)
    assert p.cues == [] and all(w == DEFAULT_FIELD_WEIGHTS for _, w in p.terms) and "from" in terms(p)
