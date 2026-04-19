"""Personality plugins — each assembles its own cogs, prefix, and intents."""

from codi.personalities.base import Personality
from codi.personalities.codi import CodiPersonality
from codi.personalities.wooloo import WoolooPersonality

_REGISTRY: dict[str, type[Personality]] = {
    "codi": CodiPersonality,
    "wooloo": WoolooPersonality,
}


def get_personality(name: str) -> type[Personality]:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown personality {name!r}. Known: {sorted(_REGISTRY)}") from exc


__all__ = ["Personality", "CodiPersonality", "WoolooPersonality", "get_personality"]
