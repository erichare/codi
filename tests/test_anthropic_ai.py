from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from codi.services import anthropic_ai
from codi.services.anthropic_ai import AnthropicError, WoolooAI


def _stub_client(content_blocks: list[object]) -> MagicMock:
    """Build a MagicMock that mimics the AsyncAnthropic client surface we use."""
    response = MagicMock()
    response.content = content_blocks
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=response)
    client.close = AsyncMock()
    return client


def _text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def test_unavailable_without_api_key() -> None:
    ai = WoolooAI(api_key=None, model="claude-sonnet-4-6")
    assert ai.is_available is False


@pytest.mark.asyncio
async def test_reply_without_api_key_raises() -> None:
    ai = WoolooAI(api_key=None, model="claude-sonnet-4-6")
    with pytest.raises(AnthropicError):
        await ai.reply("hello")


@pytest.mark.asyncio
async def test_reply_returns_joined_text(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _stub_client([_text_block("Baaa~ "), _text_block("hello!")])
    monkeypatch.setattr(anthropic_ai, "AsyncAnthropic", lambda api_key: client)

    ai = WoolooAI(api_key="test-key", model="claude-sonnet-4-6")
    result = await ai.reply("hi")

    assert result == "Baaa~ hello!"
    client.messages.create.assert_awaited_once()
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]
    assert "Wooloo" in kwargs["system"]


@pytest.mark.asyncio
async def test_reply_raises_on_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _stub_client([])
    monkeypatch.setattr(anthropic_ai, "AsyncAnthropic", lambda api_key: client)

    ai = WoolooAI(api_key="test-key", model="claude-sonnet-4-6")
    with pytest.raises(AnthropicError):
        await ai.reply("hi")


@pytest.mark.asyncio
async def test_reply_ignores_non_text_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    non_text = MagicMock()
    non_text.type = "tool_use"  # not "text" — should be skipped
    client = _stub_client([non_text, _text_block("Baaa~")])
    monkeypatch.setattr(anthropic_ai, "AsyncAnthropic", lambda api_key: client)

    ai = WoolooAI(api_key="test-key", model="claude-sonnet-4-6")
    result = await ai.reply("hi")
    assert result == "Baaa~"


@pytest.mark.asyncio
async def test_aclose_on_unconfigured_is_safe() -> None:
    ai = WoolooAI(api_key=None, model="claude-sonnet-4-6")
    await ai.aclose()  # should not raise
