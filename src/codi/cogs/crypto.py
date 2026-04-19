"""CODI's crypto cog — commands for price lookups and forecast charts."""

from __future__ import annotations

import io
import logging
from typing import Literal

import discord
from discord.ext import commands

from codi.services.crypto_api import (
    CoinInfo,
    CryptoApiClient,
    CryptoApiError,
    Horizon,
    ModelInfo,
    normalize_coin,
)

LegacyAction = Literal["price", "predictions", "unknown"]

log = logging.getLogger(__name__)

_EMBED_COLOR = discord.Color.from_rgb(247, 147, 26)  # Bitcoin orange-ish


class CryptoCog(commands.Cog, name="Crypto"):
    """`!price`, `!predict`, `!collage`, `!models`, `!coins`."""

    def __init__(self, bot: commands.Bot, api: CryptoApiClient) -> None:
        self.bot = bot
        self.api = api

    # ── price ─────────────────────────────────────────────────────

    @commands.command(name="price", aliases=("p",))
    async def price(self, ctx: commands.Context, coin: str = "btc") -> None:
        """Show the latest USD price for *coin* (ticker or CoinGecko ID)."""
        try:
            point = await self.api.latest_price(coin)
        except CryptoApiError as exc:
            await ctx.reply(f"⚠️ {exc}")
            return

        coin_id = normalize_coin(coin)
        embed = discord.Embed(
            title=f"{coin_id.title()} — latest price",
            description=f"**${point.price:,.2f}** USD",
            color=_EMBED_COLOR,
        )
        embed.set_footer(text=f"as of {point.date.isoformat()}")
        await ctx.reply(embed=embed)

    # ── predict ───────────────────────────────────────────────────

    @commands.command(name="predict", aliases=("forecast",))
    async def predict(
        self,
        ctx: commands.Context,
        coin: str = "btc",
        horizon: Literal["short", "long"] = "short",
    ) -> None:
        """Show the latest forecast chart for *coin*.

        Usage: `!predict btc` (short-term) · `!predict btc long` (long-term)
        """
        if horizon not in ("short", "long"):
            await ctx.reply("Horizon must be `short` or `long`.")
            return

        async with ctx.typing():
            try:
                chart = await self.api.latest_chart(coin, horizon=horizon)
            except CryptoApiError as exc:
                await ctx.reply(f"⚠️ {exc}")
                return

        coin_id = normalize_coin(coin)
        filename = f"{coin_id}_{horizon}.png"
        file = discord.File(io.BytesIO(chart.data), filename=filename)
        embed = discord.Embed(
            title=f"{coin_id.title()} — {horizon}-term forecast",
            color=_EMBED_COLOR,
        )
        embed.set_image(url=f"attachment://{filename}")
        await ctx.reply(embed=embed, file=file)

    # ── collage (model comparison) ────────────────────────────────

    @commands.command(name="collage", aliases=("compare",))
    async def collage(self, ctx: commands.Context, coin: str = "btc") -> None:
        """Grid image comparing every model's latest prediction for *coin*."""
        async with ctx.typing():
            try:
                chart = await self.api.collage(coin)
            except CryptoApiError as exc:
                await ctx.reply(f"⚠️ {exc}")
                return

        coin_id = normalize_coin(coin)
        filename = f"{coin_id}_collage.png"
        file = discord.File(io.BytesIO(chart.data), filename=filename)
        embed = discord.Embed(
            title=f"{coin_id.title()} — model comparison",
            color=_EMBED_COLOR,
        )
        embed.set_image(url=f"attachment://{filename}")
        await ctx.reply(embed=embed, file=file)

    # ── models ────────────────────────────────────────────────────

    @commands.command(name="models")
    async def models(self, ctx: commands.Context) -> None:
        """List supported forecasting models."""
        items = await self.api.list_models()
        await ctx.reply(embed=_models_embed(items))

    # ── coins ─────────────────────────────────────────────────────

    @commands.command(name="coins")
    async def coins(self, ctx: commands.Context) -> None:
        """List popular cryptocurrencies known to the API."""
        items = await self.api.list_coins()
        await ctx.reply(embed=_coins_embed(items))

    # ── legacy `!return` dispatcher ───────────────────────────────
    #
    # Preserves the historical syntax in any word order:
    #   !return BTC predictions
    #   !return predictions BTC
    #   !return BTC predictions longterm
    #   !return longterm predictions BTC
    #   !return BTC price
    # Under the hood this just delegates to the modern commands above.

    @commands.command(name="return")
    async def legacy_return(self, ctx: commands.Context, *tokens: str) -> None:
        """Legacy syntax: `!return <coin> <price|predictions [longterm|shortterm]>`.

        Tokens may appear in any order.
        """
        parsed = _parse_legacy_call(tokens)
        if parsed is None:
            await ctx.reply(
                "Usage: `!return <coin> price` · "
                "`!return <coin> predictions` · "
                "`!return <coin> predictions longterm` "
                "(tokens may appear in any order)"
            )
            return
        coin, action, horizon = parsed
        if action == "price":
            await self.price(ctx, coin)
        else:
            await self.predict(ctx, coin, horizon)

    # ── error handling ────────────────────────────────────────────

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.UserInputError):
            await ctx.reply(f"⚠️ {error}")
            return
        log.exception("crypto cog error", exc_info=error)
        await ctx.reply("⚠️ Something went wrong talking to the crypto API.")


def _models_embed(items: list[ModelInfo]) -> discord.Embed:
    embed = discord.Embed(title="Forecasting models", color=_EMBED_COLOR)
    for m in items:
        embed.add_field(
            name=f"`{m.id}` — {m.name}",
            value=f"{m.description}\n*{m.category} · {m.speed}*",
            inline=False,
        )
    return embed


def _coins_embed(items: list[CoinInfo]) -> discord.Embed:
    embed = discord.Embed(title="Popular coins", color=_EMBED_COLOR)
    lines = [f"• **{c.symbol.upper()}** — {c.name} (`{c.id}`)" for c in items]
    embed.description = "\n".join(lines) if lines else "_(no coins returned)_"
    return embed


_SHORT_TERMS = frozenset({"short", "shortterm", "short-term", "near", "nearterm"})
_LONG_TERMS = frozenset({"long", "longterm", "long-term", "far", "farterm"})
_PRICE_WORDS = frozenset({"price", "prices"})
_PREDICTION_WORDS = frozenset({"prediction", "predictions", "forecast", "forecasts", "predict"})


def _classify_token(token: str) -> tuple[str, str]:
    """Return (kind, normalized) where kind is action|horizon|other."""
    t = token.lower()
    if t in _PRICE_WORDS:
        return "action", "price"
    if t in _PREDICTION_WORDS:
        return "action", "predictions"
    if t in _LONG_TERMS:
        return "horizon", "long"
    if t in _SHORT_TERMS:
        return "horizon", "short"
    return "other", token


def _parse_legacy_call(
    tokens: tuple[str, ...],
) -> tuple[str, LegacyAction, Horizon] | None:
    """Parse all tokens of `!return ...` into (coin, action, horizon), order-free.

    Returns None if no action keyword or no coin-like token is present.

    Examples:
        ("BTC", "predictions") → ("BTC", "predictions", "short")
        ("predictions", "BTC") → ("BTC", "predictions", "short")
        ("BTC", "predictions", "longterm") → ("BTC", "predictions", "long")
        ("longterm", "predictions", "BTC") → ("BTC", "predictions", "long")
        ("BTC", "price") → ("BTC", "price", "short")
    """
    action: LegacyAction | None = None
    horizon: Horizon = "short"
    coin: str | None = None

    for token in tokens:
        kind, value = _classify_token(token)
        if kind == "action":
            action = value  # type: ignore[assignment]
        elif kind == "horizon":
            horizon = value  # type: ignore[assignment]
        elif coin is None:
            coin = token  # first unclassified token wins as the coin

    if action is None or coin is None:
        return None
    return coin, action, horizon
