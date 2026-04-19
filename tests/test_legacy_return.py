from __future__ import annotations

import pytest

from codi.cogs.crypto import _parse_legacy_call


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        # Original user-first ordering
        (("BTC", "predictions"), ("BTC", "predictions", "short")),
        (("BTC", "predictions", "longterm"), ("BTC", "predictions", "long")),
        (("BTC", "predictions", "long-term"), ("BTC", "predictions", "long")),
        (("BTC", "predictions", "long"), ("BTC", "predictions", "long")),
        (("BTC", "predictions", "shortterm"), ("BTC", "predictions", "short")),
        (("BTC", "price"), ("BTC", "price", "short")),
        (("btc", "prices"), ("btc", "price", "short")),
        # Action-first ordering (requested)
        (("predictions", "BTC"), ("BTC", "predictions", "short")),
        (("predictions", "BTC", "longterm"), ("BTC", "predictions", "long")),
        (("price", "BTC"), ("BTC", "price", "short")),
        # Horizon-first, coin last
        (("longterm", "predictions", "BTC"), ("BTC", "predictions", "long")),
        # Verb variants
        (("predict", "eth"), ("eth", "predictions", "short")),
        (("forecast", "sol", "long"), ("sol", "predictions", "long")),
        # Case-insensitive keywords, original coin casing preserved
        (("PREDICTIONS", "BtC"), ("BtC", "predictions", "short")),
    ],
)
def test_parse_legacy_call_success(tokens: tuple[str, ...], expected: tuple[str, str, str]) -> None:
    assert _parse_legacy_call(tokens) == expected


@pytest.mark.parametrize(
    "tokens",
    [
        (),
        ("BTC",),  # no action keyword
        ("predictions",),  # no coin
        ("longterm", "predictions"),  # no coin
    ],
)
def test_parse_legacy_call_rejects(tokens: tuple[str, ...]) -> None:
    assert _parse_legacy_call(tokens) is None
