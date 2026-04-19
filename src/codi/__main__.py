"""CLI entry point: ``python -m codi`` or ``codi`` after install."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from dotenv import load_dotenv

from codi.bot import run_all, run_single
from codi.config import Settings
from codi.personalities import get_personality


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    # Keep discord.py a touch quieter than our code at INFO.
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="codi",
        description="Run the codi Discord bot(s).",
    )
    parser.add_argument(
        "--personality",
        choices=("codi", "wooloo"),
        help="Run only this personality. Default: run every configured personality.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = _parse_args(argv)
    settings = Settings()
    _configure_logging(settings.log_level)

    if args.personality is None:
        try:
            asyncio.run(run_all(settings))
        except KeyboardInterrupt:
            return 0
        return 0

    # Single-personality mode: validate its token exists first.
    get_personality(args.personality)  # raises on unknown
    token = (
        settings.codi_bot_token if args.personality == "codi" else settings.wooloo_bot_token
    )
    if token is None or not token.get_secret_value():
        print(
            f"error: no bot token for {args.personality!r} — "
            f"set {args.personality.upper()}_BOT_TOKEN.",
            file=sys.stderr,
        )
        return 2

    try:
        asyncio.run(run_single(args.personality, token.get_secret_value(), settings))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
