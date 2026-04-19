"""Pre-programmed responses for Wooloo's uplift mode.

Kept in a plain tuple so the list is easy to edit without touching the cog.
"""

from __future__ import annotations

import secrets

UPLIFT_QUOTES: tuple[str, ...] = (
    "Baaa~ you've got this. One small step at a time. 🐑",
    "Fluffy reminder: rest is productive too. Take a breath.",
    "Whatever you're carrying, you don't have to carry it alone today.",
    "You are doing better than you think you are. Honest.",
    "The world is a little softer because you're in it. Baaa~",
    "Progress doesn't have to be loud to be real.",
    "Whenever you're ready, and not a moment before.",
    "Be patient with yourself. You're learning a new chapter.",
    "If no one's told you today: I'm proud of you.",
    "Small kindnesses count — especially to yourself.",
    "Baaa~ your pace is the right pace.",
    "You are allowed to start over as many times as you need.",
    "The hard part will pass. The softer part will find you.",
    "You don't owe anyone a perfect version of yourself.",
    "A good day doesn't have to be a big day.",
    "Hey — you showed up. That already counts.",
    "Be gentle. You're doing something hard.",
    "Baaa! Today is a good day for a tiny, brave thing.",
    "You are more resilient than the hardest week you've had.",
    "Take the walk. Drink the water. Text the friend. Baaa~",
)


def random_uplift() -> str:
    """Return a random uplift quote using a cryptographically-secure RNG."""
    return secrets.choice(UPLIFT_QUOTES)
