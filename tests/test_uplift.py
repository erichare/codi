from __future__ import annotations

from codi.data.uplift_quotes import UPLIFT_QUOTES, random_uplift


def test_random_uplift_returns_known_quote() -> None:
    assert random_uplift() in UPLIFT_QUOTES


def test_uplift_pool_is_nontrivial() -> None:
    assert len(UPLIFT_QUOTES) >= 10
    assert len(set(UPLIFT_QUOTES)) == len(UPLIFT_QUOTES)  # no duplicates
