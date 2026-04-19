"""Wooloo — the Pokemon/AI personality."""

from __future__ import annotations

import discord
from discord.ext import commands

from codi.cogs.wooloo import WoolooCog
from codi.personalities.base import Personality
from codi.services.anthropic_ai import WoolooAI
from codi.services.pokemon_api import PokemonApiClient


class WoolooPersonality(Personality):
    name = "wooloo"

    def command_prefix(self) -> str:
        return self.settings.wooloo_command_prefix

    def activity(self) -> discord.BaseActivity:
        return discord.Activity(type=discord.ActivityType.listening, name="@mentions 🐑")

    async def setup(self, bot: commands.Bot) -> None:
        pokemon = PokemonApiClient(
            self.settings.pokemon_api_base_url,
            timeout=self.settings.http_timeout_seconds,
        )
        await pokemon.__aenter__()
        ai = WoolooAI(
            api_key=(
                self.settings.anthropic_api_key.get_secret_value()
                if self.settings.anthropic_api_key
                else None
            ),
            model=self.settings.anthropic_model,
        )
        bot._wooloo_pokemon_api = pokemon  # type: ignore[attr-defined]
        bot._wooloo_ai = ai  # type: ignore[attr-defined]
        await bot.add_cog(
            WoolooCog(
                bot,
                pokemon=pokemon,
                ai=ai,
                default_mode=self.settings.wooloo_default_mode,
            )
        )

    async def teardown(self, bot: commands.Bot) -> None:
        pokemon: PokemonApiClient | None = getattr(bot, "_wooloo_pokemon_api", None)
        ai: WoolooAI | None = getattr(bot, "_wooloo_ai", None)
        if pokemon is not None:
            await pokemon.aclose()
        if ai is not None:
            await ai.aclose()
