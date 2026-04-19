"""Async client for the Crypto Predictions API.

The API is documented at:
    https://crypto-predictions-production-6b02.up.railway.app/openapi.json

Only the endpoints the Discord bot actually uses are wrapped here.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Literal
from urllib.parse import quote

import httpx

# Transient upstream failures — worth a retry before giving up.
_RETRY_STATUSES = frozenset({502, 503, 504})
_MAX_ATTEMPTS = 3
_INITIAL_BACKOFF_SECONDS = 0.8

Horizon = Literal["short", "long"]

# CoinGecko IDs are lowercase slugs. We accept common ticker shortcuts from users
# and map them to CoinGecko IDs for a friendlier UX.
_TICKER_ALIASES: dict[str, str] = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "ada": "cardano",
    "xrp": "ripple",
    "doge": "dogecoin",
    "dot": "polkadot",
    "ltc": "litecoin",
    "bnb": "binancecoin",
    "avax": "avalanche-2",
    "matic": "matic-network",
    "link": "chainlink",
    "trx": "tron",
    "xlm": "stellar",
    "atom": "cosmos",
}


def normalize_coin(user_input: str) -> str:
    """Map a user-supplied coin string to a CoinGecko coin ID.

    Accepts tickers (``btc``) and full IDs (``bitcoin``) case-insensitively.
    """
    key = user_input.strip().lower()
    return _TICKER_ALIASES.get(key, key)


@dataclass(frozen=True, slots=True)
class CoinInfo:
    id: str
    name: str
    symbol: str


@dataclass(frozen=True, slots=True)
class ModelInfo:
    id: str
    name: str
    description: str
    category: str
    speed: str


@dataclass(frozen=True, slots=True)
class PricePoint:
    date: date
    price: float


@dataclass(frozen=True, slots=True)
class ChartImage:
    data: bytes
    content_type: str


class CryptoApiError(RuntimeError):
    """Raised when the Crypto Predictions API returns an unexpected response."""


class CryptoApiClient:
    """Async client for the `/api/v1/*` endpoints of Crypto Predictions."""

    def __init__(self, base_url: str, *, timeout: float = 20.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> CryptoApiClient:
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("CryptoApiClient must be used as an async context manager.")
        return self._client

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        """Retry transient network/5xx failures, then convert to CryptoApiError."""
        client = self._require_client()
        delay = _INITIAL_BACKOFF_SECONDS
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = await client.request(method, path, **kwargs)  # type: ignore[arg-type]
            except httpx.RequestError as exc:
                if attempt == _MAX_ATTEMPTS - 1:
                    raise CryptoApiError(
                        f"Could not reach the crypto API ({exc.__class__.__name__}). "
                        "Try again in a moment."
                    ) from exc
            else:
                if response.status_code not in _RETRY_STATUSES:
                    return response
                if attempt == _MAX_ATTEMPTS - 1:
                    return response
            await asyncio.sleep(delay)
            delay *= 2
        raise CryptoApiError("Exhausted retry attempts.")  # defensive; not reachable

    @staticmethod
    def _ensure_ok(response: httpx.Response, *, context: str = "") -> None:
        """Convert any remaining non-success status into a friendly CryptoApiError."""
        if response.is_success:
            return
        suffix = f" ({context})" if context else ""
        if 500 <= response.status_code < 600:
            raise CryptoApiError(
                f"Crypto API returned {response.status_code}{suffix}. "
                "It's probably waking up or under load — try again in a few seconds."
            )
        raise CryptoApiError(f"Crypto API returned {response.status_code}{suffix}.")

    async def health(self) -> dict[str, object]:
        r = await self._request("GET", "/api/v1/health")
        self._ensure_ok(r, context="health")
        return r.json()

    async def list_coins(self) -> list[CoinInfo]:
        r = await self._request("GET", "/api/v1/coins")
        self._ensure_ok(r, context="coins")
        payload = r.json()
        return [CoinInfo(**item) for item in payload.get("items", [])]

    async def list_models(self) -> list[ModelInfo]:
        r = await self._request("GET", "/api/v1/models")
        self._ensure_ok(r, context="models")
        payload = r.json()
        return [ModelInfo(**item) for item in payload.get("items", [])]

    async def get_prices(self, coin: str) -> list[PricePoint]:
        """Return historical daily prices (USD) for *coin*, oldest first."""
        coin_id = normalize_coin(coin)
        r = await self._request("GET", f"/api/v1/coins/{quote(coin_id, safe='')}/prices")
        if r.status_code == 404:
            raise CryptoApiError(f"Unknown coin: {coin_id!r}")
        self._ensure_ok(r, context=f"prices/{coin_id}")
        payload = r.json()
        return [
            PricePoint(date=date.fromisoformat(p["date"]), price=float(p["price"]))
            for p in payload.get("prices", [])
        ]

    async def latest_price(self, coin: str) -> PricePoint:
        """Return the most recent price point for *coin*."""
        prices = await self.get_prices(coin)
        if not prices:
            raise CryptoApiError(f"No price data available for {coin!r}")
        return prices[-1]

    async def latest_chart(
        self,
        coin: str,
        *,
        horizon: Horizon = "short",
        months: int = 12,
    ) -> ChartImage:
        """Fetch the most recent forecast chart as a PNG."""
        coin_id = normalize_coin(coin)
        r = await self._request(
            "GET",
            f"/api/v1/predictions/by-coin/{quote(coin_id, safe='')}/latest",
            params={"horizon": horizon, "months": months},
        )
        if r.status_code == 404:
            raise CryptoApiError(
                f"No {horizon}-term forecast available yet for {coin_id!r}. "
                "Try generating one on the dashboard first."
            )
        self._ensure_ok(r, context=f"chart/{coin_id}/{horizon}")
        return ChartImage(
            data=r.content,
            content_type=r.headers.get("content-type", "image/png"),
        )

    async def collage(self, coin: str, *, cols: int = 3) -> ChartImage:
        """Fetch the model-comparison collage PNG for *coin*."""
        coin_id = normalize_coin(coin)
        r = await self._request(
            "GET",
            f"/api/v1/predictions/by-coin/{quote(coin_id, safe='')}/collage",
            params={"cols": cols},
        )
        if r.status_code == 404:
            raise CryptoApiError(f"No predictions yet for {coin_id!r}")
        self._ensure_ok(r, context=f"collage/{coin_id}")
        return ChartImage(
            data=r.content,
            content_type=r.headers.get("content-type", "image/png"),
        )
