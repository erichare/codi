from __future__ import annotations

from types import SimpleNamespace

from codi.cogs.wooloo import _is_direct_mention, _strip_mentions


def _msg(content: str, *, mentions: list[object], mention_everyone: bool = False):
    return SimpleNamespace(
        content=content,
        mentions=mentions,
        mention_everyone=mention_everyone,
    )


def test_is_direct_mention_true_when_bot_in_mentions() -> None:
    me = SimpleNamespace(id=42)
    msg = _msg("<@42> hi", mentions=[me])
    assert _is_direct_mention(msg, me) is True


def test_is_direct_mention_false_for_everyone() -> None:
    me = SimpleNamespace(id=42)
    msg = _msg("@everyone pay attention", mentions=[me], mention_everyone=True)
    assert _is_direct_mention(msg, me) is False


def test_is_direct_mention_false_when_someone_else() -> None:
    me = SimpleNamespace(id=42)
    other = SimpleNamespace(id=99)
    msg = _msg("<@99> hi", mentions=[other])
    assert _is_direct_mention(msg, me) is False


def test_strip_mentions_removes_all_variants() -> None:
    me = SimpleNamespace(id=42)
    assert _strip_mentions("<@42> <@!42> hello", me) == "  hello"


def test_strip_mentions_leaves_other_text_alone() -> None:
    me = SimpleNamespace(id=42)
    assert _strip_mentions("no mention here", me) == "no mention here"
