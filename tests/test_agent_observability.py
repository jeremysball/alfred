from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from alfred.agent import Agent, ToolCall, ToolEnd, ToolOutput, ToolStart


class _StreamingTool:
    def __init__(self, name: str, chunks: list[str], error: Exception | None = None) -> None:
        self.name = name
        self._chunks = chunks
        self._error = error

    async def validate_and_run_stream(self, arguments: dict[str, Any]) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk
        if self._error is not None:
            raise self._error


@pytest.mark.asyncio
async def test_execute_tool_with_events_logs_tool_lifecycle_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    agent = Agent(llm=object(), tools=object())
    call = ToolCall(
        id="call_123",
        name="lookup",
        arguments={"path": "docs.txt", "query": "needle"},
    )
    tool = _StreamingTool(name="lookup", chunks=["alpha", "beta"])
    events: list[object] = []

    def on_event(event: object) -> None:
        events.append(event)

    with caplog.at_level("DEBUG", logger="alfred.agent"):
        result = await agent._execute_tool_with_events(call, tool, on_event)

    assert result == "alphabeta"
    assert len(events) == 4
    assert isinstance(events[0], ToolStart)
    assert isinstance(events[1], ToolOutput)
    assert isinstance(events[2], ToolOutput)
    assert isinstance(events[3], ToolEnd)
    assert events[3].result == "alphabeta"
    assert events[3].is_error is False

    agent_messages = [record.message for record in caplog.records if record.name == "alfred.agent"]
    assert any(message.startswith("event=tools.tool.start") for message in agent_messages)
    assert any(message.startswith("event=tools.tool.completed") for message in agent_messages)
    assert any("tool_call_id=call_123" in message for message in agent_messages)
    assert any("tool_name=lookup" in message for message in agent_messages)
    assert any("argument_count=2" in message for message in agent_messages)
    assert any('argument_keys=["path","query"]' in message for message in agent_messages)
    assert any("chunks=2" in message for message in agent_messages)
    assert any("output_chars=9" in message for message in agent_messages)
    assert any("is_error=false" in message for message in agent_messages)
    assert any("duration_ms=" in message for message in agent_messages)
    assert not any("alpha" in message or "beta" in message for message in agent_messages)


@pytest.mark.asyncio
async def test_execute_tool_with_events_logs_tool_failure_boundary(
    caplog: pytest.LogCaptureFixture,
) -> None:
    agent = Agent(llm=object(), tools=object())
    call = ToolCall(id="call_456", name="lookup", arguments={"path": "docs.txt"})
    tool = _StreamingTool(name="lookup", chunks=["partial"], error=ValueError("boom"))
    events: list[object] = []

    def on_event(event: object) -> None:
        events.append(event)

    with caplog.at_level("DEBUG", logger="alfred.agent"):
        result = await agent._execute_tool_with_events(call, tool, on_event)

    assert result == "partialError executing lookup: boom"
    assert len(events) == 4
    assert isinstance(events[0], ToolStart)
    assert isinstance(events[1], ToolOutput)
    assert isinstance(events[2], ToolOutput)
    assert isinstance(events[3], ToolEnd)
    assert events[3].result == "partialError executing lookup: boom"
    assert events[3].is_error is True

    agent_messages = [record.message for record in caplog.records if record.name == "alfred.agent"]
    assert any(message.startswith("event=tools.tool.start") for message in agent_messages)
    assert any(message.startswith("event=tools.tool.completed") for message in agent_messages)
    assert any("tool_call_id=call_456" in message for message in agent_messages)
    assert any("chunks=1" in message for message in agent_messages)
    assert any("output_chars=" in message for message in agent_messages)
    assert any("is_error=true" in message for message in agent_messages)
    assert any("error_type=ValueError" in message for message in agent_messages)
    assert any("duration_ms=" in message for message in agent_messages)
