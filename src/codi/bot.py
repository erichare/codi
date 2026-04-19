"""Bot assembly and runner."""

from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from codi.config import Settings
from codi.personalities import Personality, get_personality

log = logging.getLogger(__name__)


class CodiBot(commands.Bot):
    """A `commands.Bot` subclass that delegates setup to a `Personality`."""

    def __init__(self, personality: Personality) -> None:
        super().__init__(
            command_prefix=personality.command_prefix(),
            intents=personality.intents(),
            activity=personality.activity(),
            help_command=commands.DefaultHelpCommand(no_category="General"),
        )
        self.personality = personality

    async def setup_hook(self) -> None:
        log.info("Setting up %s bot", self.personality.name)
        await self.personality.setup(self)

    async def close(self) -> None:
        try:
            await self.personality.teardown(self)
        finally:
            await super().close()

    async def on_ready(self) -> None:
        user = self.user
        if user is not None:
            log.info(
                "%s ready — logged in as %s (id=%s) in %d guild(s)",
                self.personality.name,
                user,
                user.id,
                len(self.guilds),
            )


async def run_single(personality_name: str, token: str, settings: Settings) -> None:
    """Run one bot for one personality."""
    cls = get_personality(personality_name)
    personality = cls(settings)
    bot = CodiBot(personality)
    try:
        await bot.start(token)
    except discord.LoginFailure:
        log.error("Invalid Discord token for %s personality", personality_name)
        raise
    finally:
        if not bot.is_closed():
            await bot.close()


async def run_all(settings: Settings) -> None:
    """Launch every configured personality in parallel."""
    pairs = settings.configured_personalities()
    if not pairs:
        raise RuntimeError(
            "No Discord tokens configured — set CODI_BOT_TOKEN and/or WOOLOO_BOT_TOKEN."
        )
    log.info(
        "Launching personalities: %s",
        ", ".join(name for name, _ in pairs),
    )
    tasks = [
        asyncio.create_task(
            run_single(name, token.get_secret_value(), settings),
            name=f"bot-{name}",
        )
        for name, token in pairs
    ]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()
        raise
