from packages.search.query.context_aware_normalization import (
    ContextAwareQueryNormalizer,
)


def make_normalizer() -> ContextAwareQueryNormalizer:
    return ContextAwareQueryNormalizer(
        aliases={
            "ali": ("alice", "morgan"),
            "ally": ("alice", "moreno"),
            "oh": ("omar", "hassan", "hussein"),
            "dan": ("daniel", "kim"),
        },
        known_full_names={
            ("alice", "morgan"),
            ("alice", "moreno"),
            ("fatima", "ali"),
            ("omar", "hassan"),
            ("omar", "hussein"),
            # Generalization fixture: surname overlaps standalone alias `dan`.
            ("miriam", "dan"),
        },
        misspellings={"rankng": "ranking"},
        hyphenations={"move-over": ("move", "over", "moveover")},
    )


def test_standalone_alias_is_expanded() -> None:
    result = make_normalizer().normalize("emails from Ali")

    assert {"ali", "alice", "morgan"}.issubset(result.terms)
    assert "alias" in result.cohorts
    assert result.suppressed_aliases == ()


def test_full_name_suppresses_overlapping_alias() -> None:
    result = make_normalizer().normalize("emails from Fatima Ali")

    assert {"fatima", "ali"}.issubset(result.terms)
    assert "alice" not in result.terms
    assert "morgan" not in result.terms
    assert "alias_collision" in result.cohorts
    assert result.suppressed_aliases[0].phrase == "fatima ali"
    assert result.suppressed_aliases[0].reason == "explicit_full_name"


def test_second_historical_collision_query_is_suppressed() -> None:
    result = make_normalizer().normalize("rollout from Fatima Ali")

    assert "alice" not in result.terms
    assert "morgan" not in result.terms
    assert len(result.suppressed_aliases) == 1


def test_generalization_full_name_is_not_a_special_case() -> None:
    result = make_normalizer().normalize("updates from Miriam Dan")

    assert {"miriam", "dan"}.issubset(result.terms)
    assert "daniel" not in result.terms
    assert "kim" not in result.terms
    assert result.suppressed_aliases[0].phrase == "miriam dan"


def test_other_alias_behavior_is_preserved() -> None:
    result = make_normalizer().normalize("spend plan from Ally")

    assert {"ally", "alice", "moreno"}.issubset(result.terms)
    assert "alias" in result.cohorts


def test_dotted_initial_behavior_is_preserved() -> None:
    result = make_normalizer().normalize("architecture from O.H.")

    assert {"oh", "omar", "hassan", "hussein"}.issubset(result.terms)
    assert {"initials", "alias"}.issubset(result.cohorts)


def test_misspelling_behavior_is_preserved() -> None:
    result = make_normalizer().normalize("latest rankng experiment")

    assert "rankng" in result.terms
    assert "ranking" in result.terms
    assert "misspelling" in result.cohorts


def test_hyphenation_behavior_is_preserved() -> None:
    result = make_normalizer().normalize("move-over from OH")

    assert {"move", "over", "moveover"}.issubset(result.terms)
    assert "hyphenation" in result.cohorts


def test_ordinary_query_is_untouched() -> None:
    result = make_normalizer().normalize("latest Atlas ranking")

    assert result.terms == ("latest", "atlas", "ranking")
    assert result.cohorts == ()
    assert result.suppressed_aliases == ()


def test_longest_known_name_match_wins() -> None:
    normalizer = ContextAwareQueryNormalizer(
        aliases={"ali": ("alice", "morgan")},
        known_full_names={
            ("fatima", "ali"),
            ("dr", "fatima", "ali"),
        },
    )

    result = normalizer.normalize("mail from Dr Fatima Ali")

    assert result.suppressed_aliases[0].phrase == "dr fatima ali"
    assert "alice" not in result.terms
