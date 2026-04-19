"""CODI — the crypto/tech personality."""

from __future__ import annotations

import discord
from discord.ext import commands

from codi.cogs.crypto import CryptoCog
from codi.personalities.base import Personality
from codi.services.crypto_api import CryptoApiClient


class CodiPersonality(Personality):
    name = "codi"

    def command_prefix(self) -> str:
        return self.settings.codi_command_prefix

    def activity(self) -> discord.BaseActivity:
        return discord.Activity(type=discord.ActivityType.watching, name="BTC charts")

    async def setup(self, bot: commands.Bot) -> None:
        api = CryptoApiClient(
            self.settings.crypto_api_base_url,
            timeout=self.settings.http_timeout_seconds,
        )
        await api.__aenter__()
        bot._codi_crypto_api = api  # type: ignore[attr-defined]
        await bot.add_cog(CryptoCog(bot, api))

    async def teardown(self, bot: commands.Bot) -> None:
        api: CryptoApiClient | None = getattr(bot, "_codi_crypto_api", None)
        if api is not None:
            await api.aclose()
