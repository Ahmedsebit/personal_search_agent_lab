from packages.datasets.generator import build_dataset


def test_generation_is_deterministic():
    first = build_dataset(20, 8, 42)
    second = build_dataset(20, 8, 42)
    assert first == second
    assert len(first[0]) == 20
    assert len(first[1]) == 8
    assert first[2]
