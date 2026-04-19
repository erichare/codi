"""Async client for PokeAPI (https://pokeapi.co)."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import httpx


class PokemonApiError(RuntimeError):
    """Raised on unexpected responses from the Pokemon API."""


@dataclass(frozen=True, slots=True)
class Pokemon:
    id: int
    name: str
    height_dm: int  # decimeters
    weight_hg: int  # hectograms
    types: tuple[str, ...]
    abilities: tuple[str, ...]
    sprite_url: str | None

    @property
    def height_m(self) -> float:
        return self.height_dm / 10

    @property
    def weight_kg(self) -> float:
        return self.weight_hg / 10


class PokemonApiClient:
    """Minimal async wrapper around the endpoints we use."""

    def __init__(self, base_url: str, *, timeout: float = 20.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> PokemonApiClient:
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("PokemonApiClient must be used as an async context manager.")
        return self._client

    async def get_pokemon(self, name_or_id: str) -> Pokemon:
        slug = quote(name_or_id.strip().lower(), safe="")
        r = await self._require_client().get(f"/pokemon/{slug}")
        if r.status_code == 404:
            raise PokemonApiError(f"No Pokemon named {name_or_id!r}")
        r.raise_for_status()
        data = r.json()
        sprites = data.get("sprites") or {}
        sprite = (
            (sprites.get("other") or {}).get("official-artwork", {}).get("front_default")
            or sprites.get("front_default")
        )
        return Pokemon(
            id=int(data["id"]),
            name=str(data["name"]),
            height_dm=int(data["height"]),
            weight_hg=int(data["weight"]),
            types=tuple(t["type"]["name"] for t in data.get("types", [])),
            abilities=tuple(a["ability"]["name"] for a in data.get("abilities", [])),
            sprite_url=sprite,
        )
