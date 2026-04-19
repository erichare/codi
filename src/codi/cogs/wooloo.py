"""Wooloo cog — @mention chat with mode switching, plus Pokemon lookups."""

from __future__ import annotations

import logging
from typing import Literal

import discord
from discord.ext import commands

from codi.data.uplift_quotes import random_uplift
from codi.services.anthropic_ai import AnthropicError, WoolooAI
from codi.services.pokemon_api import Pokemon, PokemonApiClient, PokemonApiError

log = logging.getLogger(__name__)

Mode = Literal["ai", "uplift"]
_ALLOWED_MODES: tuple[Mode, ...] = ("ai", "uplift")

_EMBED_COLOR = discord.Color.from_rgb(230, 230, 250)  # soft lavender, matches Wooloo


class WoolooCog(commands.Cog, name="Wooloo"):
    """Handles @mentions, `!mode`, `!pokemon`."""

    def __init__(
        self,
        bot: commands.Bot,
        pokemon: PokemonApiClient,
        ai: WoolooAI,
        default_mode: Mode,
    ) -> None:
        self.bot = bot
        self.pokemon = pokemon
        self.ai = ai
        # One mode per guild — flips at runtime via `!mode`.
        self._guild_modes: dict[int, Mode] = {}
        self._default_mode: Mode = default_mode

    # ── mode helpers ──────────────────────────────────────────────

    def _mode_for(self, guild: discord.Guild | None) -> Mode:
        if guild is None:
            return self._default_mode
        return self._guild_modes.get(guild.id, self._default_mode)

    def _set_mode(self, guild: discord.Guild, mode: Mode) -> None:
        self._guild_modes[guild.id] = mode

    # ── commands ──────────────────────────────────────────────────

    @commands.command(name="mode")
    async def mode(self, ctx: commands.Context, new_mode: str | None = None) -> None:
        """Show or switch Wooloo's response mode.

        Usage: `!mode` · `!mode ai` · `!mode uplift`
        """
        if new_mode is None:
            current = self._mode_for(ctx.guild)
            await ctx.reply(
                f"Baaa~ I'm in **{current}** mode. "
                f"Switch with `{ctx.clean_prefix}mode ai` or `{ctx.clean_prefix}mode uplift`."
            )
            return

        normalized = new_mode.strip().lower()
        if normalized not in _ALLOWED_MODES:
            await ctx.reply(
                f"Mode must be one of: {', '.join(f'`{m}`' for m in _ALLOWED_MODES)}."
            )
            return
        if normalized == "ai" and not self.ai.is_available:
            await ctx.reply(
                "AI mode isn't configured on this bot — "
                "ask the admin to set `ANTHROPIC_API_KEY`."
            )
            return

        if ctx.guild is None:
            await ctx.reply("You can only switch modes inside a server.")
            return

        self._set_mode(ctx.guild, normalized)  # type: ignore[arg-type]
        await ctx.reply(f"Baaa~ now in **{normalized}** mode. 🐑")

    @commands.command(name="pokemon", aliases=("poke",))
    async def pokemon_lookup(
        self, ctx: commands.Context, *, name_or_id: str
    ) -> None:
        """Show basic info about a Pokemon by name or Pokedex ID."""
        try:
            poke = await self.pokemon.get_pokemon(name_or_id)
        except PokemonApiError as exc:
            await ctx.reply(f"⚠️ {exc}")
            return
        await ctx.reply(embed=_pokemon_embed(poke))

    @commands.command(name="uplift")
    async def uplift(self, ctx: commands.Context) -> None:
        """Send a one-off uplifting message, regardless of mode."""
        await ctx.reply(random_uplift())

    # ── @mention listener ─────────────────────────────────────────

    @commands.Cog.listener("on_message")
    async def on_mention(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        me = self.bot.user
        if me is None or not _is_direct_mention(message, me):
            return
        text = _strip_mentions(message.content, me).strip()
        if not text:
            await message.reply(random_uplift())
            return

        # Sub-commands embedded in mentions: "@wooloo mode ai" / "@wooloo pokemon wooloo".
        lowered = text.lower()
        if lowered.startswith("mode"):
            await self._handle_inline_mode(message, text[len("mode"):].strip())
            return
        if lowered.startswith(("pokemon ", "poke ")):
            _, _, rest = text.partition(" ")
            await self._handle_inline_pokemon(message, rest.strip())
            return
        if lowered in ("help", "?"):
            await message.reply(embed=_help_embed())
            return

        mode = self._mode_for(message.guild)
        if mode == "uplift":
            await message.reply(random_uplift())
            return

        async with message.channel.typing():
            try:
                reply = await self.ai.reply(text)
            except AnthropicError as exc:
                await message.reply(f"⚠️ {exc}")
                return
            except Exception:  # noqa: BLE001 — surface a friendly error
                log.exception("AI reply failed")
                await message.reply("⚠️ My brain went fuzzy for a second — try again?")
                return
        await message.reply(reply)

    async def _handle_inline_mode(
        self, message: discord.Message, arg: str
    ) -> None:
        if not arg:
            current = self._mode_for(message.guild)
            await message.reply(f"Baaa~ currently in **{current}** mode.")
            return
        normalized = arg.lower()
        if normalized not in _ALLOWED_MODES:
            await message.reply(
                f"Mode must be one of: {', '.join(f'`{m}`' for m in _ALLOWED_MODES)}."
            )
            return
        if normalized == "ai" and not self.ai.is_available:
            await message.reply(
                "AI mode isn't configured — ask the admin to set `ANTHROPIC_API_KEY`."
            )
            return
        if message.guild is None:
            await message.reply("You can only switch modes inside a server.")
            return
        self._set_mode(message.guild, normalized)  # type: ignore[arg-type]
        await message.reply(f"Baaa~ now in **{normalized}** mode. 🐑")

    async def _handle_inline_pokemon(
        self, message: discord.Message, name: str
    ) -> None:
        if not name:
            await message.reply("Tell me which Pokemon to look up, e.g. `@Wooloo pokemon pikachu`.")
            return
        try:
            poke = await self.pokemon.get_pokemon(name)
        except PokemonApiError as exc:
            await message.reply(f"⚠️ {exc}")
            return
        await message.reply(embed=_pokemon_embed(poke))

    # ── error handling ────────────────────────────────────────────

    async def cog_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.UserInputError):
            await ctx.reply(f"⚠️ {error}")
            return
        log.exception("wooloo cog error", exc_info=error)
        await ctx.reply("⚠️ Something went baaa-d. Try again?")


# ── helpers ───────────────────────────────────────────────────────


def _is_direct_mention(message: discord.Message, me: discord.abc.User) -> bool:
    """True when the bot is mentioned directly (not via @here / @everyone / role)."""
    if message.mention_everyone:
        return False
    return any(u.id == me.id for u in message.mentions)


def _strip_mentions(content: str, me: discord.abc.User) -> str:
    """Remove the bot's own mention tokens from *content*."""
    return content.replace(f"<@{me.id}>", "").replace(f"<@!{me.id}>", "")


def _pokemon_embed(poke: Pokemon) -> discord.Embed:
    embed = discord.Embed(
        title=f"#{poke.id:03d} — {poke.name.title()}",
        color=_EMBED_COLOR,
    )
    embed.add_field(name="Types", value=", ".join(t.title() for t in poke.types) or "—")
    embed.add_field(name="Abilities", value=", ".join(a.title() for a in poke.abilities) or "—")
    embed.add_field(name="Height", value=f"{poke.height_m:.1f} m")
    embed.add_field(name="Weight", value=f"{poke.weight_kg:.1f} kg")
    if poke.sprite_url:
        embed.set_thumbnail(url=poke.sprite_url)
    return embed


def _help_embed() -> discord.Embed:
    return discord.Embed(
        title="Wooloo — help",
        description=(
            "Mention me to chat. I have two modes:\n"
            "• **uplift** — pre-written encouragements\n"
            "• **ai** — a cozy AI reply (needs Anthropic API key)\n\n"
            "**Inline commands** (after `@Wooloo`):\n"
            "`mode` · `mode ai` · `mode uplift` · `pokemon <name>` · `help`\n\n"
            "**Prefix commands**:\n"
            "`!mode` · `!pokemon <name>` · `!uplift`"
        ),
        color=_EMBED_COLOR,
    )
