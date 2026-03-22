from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from alfred.llm import ChatMessage, KimiProvider, LLMError


class _FakeStream:
    def __init__(self, chunks: list[object]) -> None:
        self._chunks = chunks
        self._iterator = iter(self._chunks)

    def __aiter__(self) -> _FakeStream:
        self._iterator = iter(self._chunks)
        return self

    async def __anext__(self) -> object:
        try:
            return next(self._iterator)
        except StopIteration as exc:  # pragma: no cover - standard async iterator path
            raise StopAsyncIteration from exc


def _content_chunk(content: str) -> object:
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content, reasoning_content=None, tool_calls=None))])


def _tool_call(tool_call_id: str, name: str, arguments: str) -> object:
    return SimpleNamespace(
        id=tool_call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _chat_response(
    content: str,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    tool_calls: list[object] | None = None,
    reasoning_content: str | None = None,
) -> object:
    return SimpleNamespace(
        model="kimi-k2-5",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                    tool_calls=tool_calls,
                    reasoning_content=reasoning_content,
                )
            )
        ],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


def _build_provider(create_side_effect: object | list[object]) -> KimiProvider:
    provider = object.__new__(KimiProvider)
    provider.model = "kimi-k2-5"
    provider.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(side_effect=create_side_effect),
            )
        )
    )
    return provider


@pytest.mark.asyncio
async def test_chat_logs_request_lifecycle_and_completion_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = _build_provider(
        [
            _chat_response(
                "assistant content should stay out of logs",
                prompt_tokens=12,
                completion_tokens=6,
            )
        ]
    )

    with caplog.at_level("DEBUG", logger="alfred.llm"):
        response = await provider.chat([ChatMessage(role="user", content="hi")])

    assert response.content == "assistant content should stay out of logs"
    assert response.usage == {"prompt_tokens": 12, "completion_tokens": 6}

    messages = [record.message for record in caplog.records if record.name == "alfred.llm"]
    assert any(message.startswith("event=llm.request.start") for message in messages)
    assert any("operation=chat" in message for message in messages)
    assert any("messages=1" in message for message in messages)
    assert any("prompt_tokens=12" in message for message in messages)
    assert any("completion_tokens=6" in message for message in messages)
    assert any("duration_ms=" in message for message in messages)
    assert not any("assistant content should stay out of logs" in message for message in messages)


@pytest.mark.asyncio
async def test_chat_with_tools_logs_request_lifecycle_and_tool_counts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = _build_provider(
        [
            _chat_response(
                "tool response should stay out of logs",
                prompt_tokens=14,
                completion_tokens=8,
                tool_calls=[_tool_call("call_1", "lookup", '{"path":"test.txt"}')],
            )
        ]
    )

    with caplog.at_level("DEBUG", logger="alfred.llm"):
        response = await provider.chat_with_tools(
            [ChatMessage(role="user", content="hello")],
            tools=[{"type": "function", "function": {"name": "lookup"}}],
        )

    assert response.content == "tool response should stay out of logs"
    assert response.usage == {"prompt_tokens": 14, "completion_tokens": 8}
    assert response.tool_calls == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "lookup", "arguments": '{"path":"test.txt"}'},
        }
    ]

    messages = [record.message for record in caplog.records if record.name == "alfred.llm"]
    assert any(message.startswith("event=llm.request.start") for message in messages)
    assert any("operation=chat_with_tools" in message for message in messages)
    assert any("messages=1" in message for message in messages)
    assert any("tools=1" in message for message in messages)
    assert any("tool_calls=1" in message for message in messages)
    assert any("prompt_tokens=14" in message for message in messages)
    assert any("completion_tokens=8" in message for message in messages)
    assert any("duration_ms=" in message for message in messages)
    assert not any("tool response should stay out of logs" in message for message in messages)


@pytest.mark.asyncio
async def test_stream_chat_logs_request_lifecycle_and_retry(caplog: pytest.LogCaptureFixture) -> None:
    provider = _build_provider(
        [
            RuntimeError("temporary failure"),
            _FakeStream([_content_chunk("Hel"), _content_chunk("lo")]),
        ]
    )

    with (
        caplog.at_level("DEBUG", logger="alfred.llm"),
        patch("alfred.llm.asyncio.sleep", new=AsyncMock()),
        patch("alfred.llm.random.random", return_value=0.0),
    ):
        output = [chunk async for chunk in provider.stream_chat([ChatMessage(role="user", content="hi")])]

    assert output == ["Hel", "lo"]

    messages = [record.message for record in caplog.records if record.name == "alfred.llm"]
    assert any(message.startswith("event=llm.request.start") for message in messages)
    assert any(message.startswith("event=llm.request.retry") for message in messages)
    assert any(message.startswith("event=llm.request.first_token") for message in messages)
    assert any(message.startswith("event=llm.request.completed") for message in messages)


@pytest.mark.asyncio
async def test_stream_chat_with_tools_logs_completion(caplog: pytest.LogCaptureFixture) -> None:
    provider = _build_provider(
        [
            _FakeStream([_content_chunk("alpha"), _content_chunk("beta")]),
        ]
    )

    with caplog.at_level("DEBUG", logger="alfred.llm"):
        output = [
            chunk
            async for chunk in provider.stream_chat_with_tools(
                [ChatMessage(role="user", content="hello")],
                tools=[{"type": "function", "function": {"name": "lookup"}}],
            )
        ]

    assert output == ["alpha", "beta"]

    messages = [record.message for record in caplog.records if record.name == "alfred.llm"]
    assert any(message.startswith("event=llm.request.start") for message in messages)
    assert any(message.startswith("event=llm.request.first_token") for message in messages)
    assert any(message.startswith("event=llm.request.completed") for message in messages)


@pytest.mark.asyncio
async def test_stream_chat_logs_failed_request_after_retries_are_exhausted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = _build_provider(RuntimeError("temporary failure"))

    with (
        caplog.at_level("DEBUG", logger="alfred.llm"),
        patch("alfred.llm.asyncio.sleep", new=AsyncMock()),
        patch("alfred.llm.random.random", return_value=0.0),
        pytest.raises(LLMError, match="Unexpected error: temporary failure"),
    ):
        [chunk async for chunk in provider.stream_chat([ChatMessage(role="user", content="hi")])]

    messages = [record.message for record in caplog.records if record.name == "alfred.llm"]
    assert any(message.startswith("event=llm.request.start") for message in messages)
    assert any(message.startswith("event=llm.request.retry") for message in messages)
    assert any(message.startswith("event=llm.request.failed") for message in messages)
    assert any("operation=stream_chat" in message for message in messages)
    assert any("error_type=RuntimeError" in message for message in messages)
    assert any('error="temporary failure"' in message for message in messages)


@pytest.mark.asyncio
async def test_stream_chat_with_tools_logs_failed_request_after_retries_are_exhausted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = _build_provider(RuntimeError("temporary failure"))

    with (
        caplog.at_level("DEBUG", logger="alfred.llm"),
        patch("alfred.llm.asyncio.sleep", new=AsyncMock()),
        patch("alfred.llm.random.random", return_value=0.0),
        pytest.raises(LLMError, match="Unexpected error: temporary failure"),
    ):
        [
            chunk
            async for chunk in provider.stream_chat_with_tools(
                [ChatMessage(role="user", content="hello")],
                tools=[{"type": "function", "function": {"name": "lookup"}}],
            )
        ]

    messages = [record.message for record in caplog.records if record.name == "alfred.llm"]
    assert any(message.startswith("event=llm.request.start") for message in messages)
    assert any(message.startswith("event=llm.request.retry") for message in messages)
    assert any(message.startswith("event=llm.request.failed") for message in messages)
    assert any("operation=stream_chat_with_tools" in message for message in messages)
    assert any("tools=1" in message for message in messages)
    assert any("error_type=RuntimeError" in message for message in messages)
    assert any('error="temporary failure"' in message for message in messages)
