from __future__ import annotations

import pytest

from codi.services import crypto_api
from codi.services.crypto_api import (
    CryptoApiClient,
    CryptoApiError,
    normalize_coin,
)


@pytest.fixture(autouse=True)
def _fast_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zero out retry backoff so tests stay fast."""
    monkeypatch.setattr(crypto_api, "_INITIAL_BACKOFF_SECONDS", 0)


@pytest.mark.parametrize(
    ("user_input", "expected"),
    [
        ("btc", "bitcoin"),
        ("BTC", "bitcoin"),
        ("  eth  ", "ethereum"),
        ("bitcoin", "bitcoin"),
        ("unknown-coin", "unknown-coin"),
    ],
)
def test_normalize_coin(user_input: str, expected: str) -> None:
    assert normalize_coin(user_input) == expected


@pytest.mark.asyncio
async def test_latest_price_returns_last_point(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://example.test/api/v1/coins/bitcoin/prices",
        json={
            "coin": "bitcoin",
            "currency": "usd",
            "prices": [
                {"date": "2026-04-17", "price": 70000.0},
                {"date": "2026-04-18", "price": 71234.56},
            ],
        },
    )
    async with CryptoApiClient("https://example.test") as api:
        point = await api.latest_price("btc")
    assert point.price == pytest.approx(71234.56)
    assert point.date.isoformat() == "2026-04-18"


@pytest.mark.asyncio
async def test_latest_price_raises_on_empty(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://example.test/api/v1/coins/bitcoin/prices",
        json={"coin": "bitcoin", "currency": "usd", "prices": []},
    )
    async with CryptoApiClient("https://example.test") as api:
        with pytest.raises(CryptoApiError):
            await api.latest_price("btc")


@pytest.mark.asyncio
async def test_latest_chart_returns_png_bytes(httpx_mock) -> None:
    png_bytes = b"\x89PNG\r\n\x1a\nfake"
    httpx_mock.add_response(
        url="https://example.test/api/v1/predictions/by-coin/bitcoin/latest?horizon=short&months=12",
        content=png_bytes,
        headers={"content-type": "image/png"},
    )
    async with CryptoApiClient("https://example.test") as api:
        chart = await api.latest_chart("btc", horizon="short")
    assert chart.data == png_bytes
    assert chart.content_type == "image/png"


@pytest.mark.asyncio
async def test_latest_chart_404_raises(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://example.test/api/v1/predictions/by-coin/doesnotexist/latest?horizon=long&months=12",
        status_code=404,
    )
    async with CryptoApiClient("https://example.test") as api:
        with pytest.raises(CryptoApiError):
            await api.latest_chart("doesnotexist", horizon="long")


@pytest.mark.asyncio
async def test_latest_chart_retries_then_succeeds_on_5xx(httpx_mock) -> None:
    url = "https://example.test/api/v1/predictions/by-coin/bitcoin/latest?horizon=short&months=12"
    httpx_mock.add_response(url=url, status_code=502)
    httpx_mock.add_response(url=url, status_code=503)
    httpx_mock.add_response(
        url=url,
        content=b"\x89PNGdata",
        headers={"content-type": "image/png"},
    )
    async with CryptoApiClient("https://example.test") as api:
        chart = await api.latest_chart("btc")
    assert chart.data == b"\x89PNGdata"


@pytest.mark.asyncio
async def test_latest_chart_persistent_5xx_raises_friendly_error(httpx_mock) -> None:
    url = "https://example.test/api/v1/predictions/by-coin/bitcoin/latest?horizon=short&months=12"
    for _ in range(3):
        httpx_mock.add_response(url=url, status_code=502)
    async with CryptoApiClient("https://example.test") as api:
        with pytest.raises(CryptoApiError) as excinfo:
            await api.latest_chart("btc")
    assert "502" in str(excinfo.value)
    assert "try again" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_latest_chart_network_error_raises_friendly(httpx_mock) -> None:
    import httpx

    url = "https://example.test/api/v1/predictions/by-coin/bitcoin/latest?horizon=short&months=12"
    for _ in range(3):
        httpx_mock.add_exception(httpx.ConnectError("boom"), url=url)
    async with CryptoApiClient("https://example.test") as api:
        with pytest.raises(CryptoApiError) as excinfo:
            await api.latest_chart("btc")
    assert "Could not reach" in str(excinfo.value)
