from __future__ import annotations

import pytest

from codi.services.pokemon_api import PokemonApiClient, PokemonApiError


@pytest.mark.asyncio
async def test_get_pokemon_parses_payload(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://pokeapi.test/pokemon/wooloo",
        json={
            "id": 831,
            "name": "wooloo",
            "height": 6,
            "weight": 65,
            "types": [{"type": {"name": "normal"}}],
            "abilities": [
                {"ability": {"name": "fluffy"}},
                {"ability": {"name": "run-away"}},
            ],
            "sprites": {
                "front_default": "https://img.test/wooloo.png",
                "other": {"official-artwork": {"front_default": "https://img.test/wooloo_art.png"}},
            },
        },
    )
    async with PokemonApiClient("https://pokeapi.test") as api:
        poke = await api.get_pokemon("Wooloo")
    assert poke.id == 831
    assert poke.name == "wooloo"
    assert poke.height_m == pytest.approx(0.6)
    assert poke.weight_kg == pytest.approx(6.5)
    assert poke.types == ("normal",)
    assert poke.abilities == ("fluffy", "run-away")
    assert poke.sprite_url == "https://img.test/wooloo_art.png"


@pytest.mark.asyncio
async def test_get_pokemon_404(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://pokeapi.test/pokemon/nopenope",
        status_code=404,
    )
    async with PokemonApiClient("https://pokeapi.test") as api:
        with pytest.raises(PokemonApiError):
            await api.get_pokemon("nopenope")
