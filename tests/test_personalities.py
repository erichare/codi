from __future__ import annotations

import pytest
from pydantic import SecretStr

from codi.config import Settings
from codi.personalities import CodiPersonality, WoolooPersonality, get_personality


def _settings(**overrides: object) -> Settings:
    defaults = {
        "codi_bot_token": SecretStr("codi-token"),
        "wooloo_bot_token": SecretStr("wooloo-token"),
    }
    return Settings.model_validate({**defaults, **overrides})


def test_get_personality_known() -> None:
    assert get_personality("codi") is CodiPersonality
    assert get_personality("wooloo") is WoolooPersonality


def test_get_personality_unknown_raises() -> None:
    with pytest.raises(ValueError):
        get_personality("mystery")


def test_configured_personalities_skips_missing_tokens() -> None:
    s = _settings(codi_bot_token=None, wooloo_bot_token=SecretStr("w"))
    names = [name for name, _ in s.configured_personalities()]
    assert names == ["wooloo"]


def test_configured_personalities_skips_empty_strings() -> None:
    s = _settings(codi_bot_token=SecretStr(""), wooloo_bot_token=SecretStr(""))
    assert s.configured_personalities() == []


def test_codi_personality_prefix_matches_settings() -> None:
    s = _settings(codi_command_prefix="?")
    p = CodiPersonality(s)
    assert p.command_prefix() == "?"
    assert p.intents().message_content is True


def test_wooloo_personality_defaults_to_uplift_mode() -> None:
    s = _settings()
    p = WoolooPersonality(s)
    assert p.settings.wooloo_default_mode == "uplift"
