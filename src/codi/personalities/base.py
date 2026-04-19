"""Base class for bot personalities.

A *personality* bundles together everything that makes one bot instance feel
different from another: its command prefix, its intents, the cogs it loads,
and any shared services those cogs depend on.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import discord
from discord.ext import commands

from codi.config import Settings


class Personality(ABC):
    """One personality → one `commands.Bot` instance."""

    #: Name used for logging and registry lookup.
    name: str = ""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def command_prefix(self) -> str:
        """Prefix used for text commands in this personality."""

    def intents(self) -> discord.Intents:
        """Discord gateway intents. Override if the personality needs more."""
        intents = discord.Intents.default()
        intents.message_content = True
        return intents

    def activity(self) -> discord.BaseActivity | None:
        """Optional rich-presence activity text."""
        return None

    @abstractmethod
    async def setup(self, bot: commands.Bot) -> None:
        """Attach cogs and any shared resources to *bot*.

        Called exactly once during ``bot.setup_hook``.
        """

    async def teardown(self, bot: commands.Bot) -> None:  # noqa: B027 — intentional no-op default
        """Release any resources held by the personality. Default: no-op."""
