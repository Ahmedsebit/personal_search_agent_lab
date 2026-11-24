from packages.search.query.normalization import normalize_query


def test_alias_expands_to_benchmark_owned_canonical_terms():
    normalized = normalize_query("budget from Dan")
    assert {"dan", "daniel", "kim"} <= set(normalized.terms)
    assert "alias" in normalized.cohorts


def test_dotted_initials_are_joined_before_alias_expansion():
    normalized = normalize_query("architecture from O.H.")
    assert "oh" in normalized.terms
    assert {"omar", "hassan", "hussein"} <= set(normalized.terms)
    assert {"initials", "alias"} <= set(normalized.cohorts)


def test_hyphenated_form_preserves_original_and_adds_compatible_forms():
    normalized = normalize_query("messages about move-over")
    assert {"move", "over", "moveover"} <= set(normalized.terms)
    assert "hyphenation" in normalized.cohorts


def test_known_misspelling_adds_canonical_form_without_dropping_raw_term():
    normalized = normalize_query("rankng experiment")
    assert {"rankng", "ranking"} <= set(normalized.terms)
    assert "misspelling" in normalized.cohorts


def test_unknown_and_ordinary_terms_are_not_semantically_expanded():
    normalized = normalize_query("Atlas architecture")
    assert normalized.terms == ("atlas", "architecture")
    assert normalized.cohorts == ("none",)
