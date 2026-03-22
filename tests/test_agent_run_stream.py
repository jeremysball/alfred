"""Tests for Agent.run_stream refactoring."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from alfred.agent import Agent, ToolCall, ToolEnd, ToolOutput, ToolStart
from alfred.llm import ChatMessage
from alfred.tools import Tool, ToolRegistry, clear_registry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry before each test."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def mock_llm():
    """Create a mock LLM provider."""
    llm = MagicMock()
    llm.stream_chat_with_tools = AsyncMock()
    return llm


@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry with test tools."""
    registry = ToolRegistry()

    # Add mock read tool
    async def mock_read_stream(arguments):
        path = arguments.get("path", "unknown")
        yield f"Contents of {path}"

    read_tool = MagicMock(spec=Tool)
    read_tool.name = "read"
    read_tool.validate_and_run_stream = mock_read_stream
    registry.register(read_tool)

    return registry


class TestExecuteToolWithEvents:
    """Tests for _execute_tool_with_events method."""

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, mock_llm, mock_tool_registry, caplog: pytest.LogCaptureFixture):
        """Test successful tool execution with events."""
        agent = Agent(mock_llm, mock_tool_registry)

        # Create mock tool
        async def mock_stream(arguments):
            yield "output chunk 1"
            yield "output chunk 2"

        tool = MagicMock(spec=Tool)
        tool.name = "test_tool"
        tool.validate_and_run_stream = mock_stream

        call = ToolCall(id="call_1", name="test_tool", arguments={"key": "value"})

        events = []

        def event_callback(event):
            events.append(event)

        with caplog.at_level("DEBUG", logger="alfred.agent"):
            result = await agent._execute_tool_with_events(call, tool, event_callback)

        assert result == "output chunk 1output chunk 2"
        assert len(events) == 4  # ToolStart, ToolOutput (x2), ToolEnd
        assert isinstance(events[0], ToolStart)
        assert events[0].tool_call_id == "call_1"
        assert events[0].tool_name == "test_tool"
        assert events[0].arguments == {"key": "value"}
        assert isinstance(events[1], ToolOutput)
        assert isinstance(events[2], ToolOutput)
        assert isinstance(events[3], ToolEnd)
        assert events[3].result == "output chunk 1output chunk 2"
        assert not events[3].is_error

        agent_messages = [record.message for record in caplog.records if record.name == "alfred.agent"]
        assert any(message.startswith("event=tools.tool.start") for message in agent_messages)
        assert any(message.startswith("event=tools.tool.completed") for message in agent_messages)
        assert any("output_chars=28" in message for message in agent_messages)

    @pytest.mark.asyncio
    async def test_execute_tool_error(self, mock_llm, mock_tool_registry, caplog: pytest.LogCaptureFixture):
        """Test tool execution with error."""
        agent = Agent(mock_llm, mock_tool_registry)

        # Create mock tool that raises exception
        async def mock_stream_error(arguments):
            yield "initial output"  # Need to yield first to make it an async generator
            raise ValueError("Something went wrong")

        tool = MagicMock(spec=Tool)
        tool.name = "error_tool"
        tool.validate_and_run_stream = mock_stream_error

        call = ToolCall(id="call_2", name="error_tool", arguments={})

        events = []

        def event_callback(event):
            events.append(event)

        with caplog.at_level("DEBUG", logger="alfred.agent"):
            result = await agent._execute_tool_with_events(call, tool, event_callback)

        assert "Error executing error_tool" in result
        assert "Something went wrong" in result
        assert len(events) == 4  # ToolStart, ToolOutput (initial), ToolOutput (error), ToolEnd
        assert isinstance(events[0], ToolStart)
        assert isinstance(events[1], ToolOutput)
        assert events[1].chunk == "initial output"
        assert isinstance(events[2], ToolOutput)
        assert "Error executing" in events[2].chunk
        assert isinstance(events[3], ToolEnd)
        assert events[3].is_error is True

        agent_messages = [record.message for record in caplog.records if record.name == "alfred.agent"]
        assert any(message.startswith("event=tools.tool.start") for message in agent_messages)
        assert any(message.startswith("event=tools.tool.completed") for message in agent_messages)
        assert any("is_error=true" in message for message in agent_messages)
        assert any("error_type=ValueError" in message for message in agent_messages)

    @pytest.mark.asyncio
    async def test_execute_tool_no_callback(self, mock_llm, mock_tool_registry):
        """Test tool execution without callback."""
        agent = Agent(mock_llm, mock_tool_registry)

        async def mock_stream(arguments):
            yield "result"

        tool = MagicMock(spec=Tool)
        tool.name = "test_tool"
        tool.validate_and_run_stream = mock_stream

        call = ToolCall(id="call_3", name="test_tool", arguments={})

        result = await agent._execute_tool_with_events(call, tool, None)

        assert result == "result"


class TestAgentRunStreamIntegration:
    """Integration tests for the refactored run_stream."""

    @pytest.mark.asyncio
    async def test_run_stream_no_tool_calls(self, mock_llm, mock_tool_registry):
        """Test full run_stream with no tool calls."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=3)

        async def mock_stream(*args, **kwargs):
            yield "Hello! This is a direct response."

        mock_llm.stream_chat_with_tools = mock_stream

        messages = [ChatMessage(role="user", content="Hi")]
        chunks = []
        async for chunk in agent.run_stream(messages):
            chunks.append(chunk)

        assert "Hello!" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_run_stream_with_tool_calls(self, mock_llm, mock_tool_registry):
        """Test full run_stream with tool execution."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=3)

        call_count = 0

        async def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                tool_calls = [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "read", "arguments": json.dumps({"path": "test.txt"})},
                    }
                ]
                yield f"[TOOL_CALLS]{json.dumps(tool_calls)}"
            else:
                yield "Here is the content"

        mock_llm.stream_chat_with_tools = mock_stream

        events = []

        def on_event(event):
            events.append(event)

        messages = [ChatMessage(role="user", content="Read file")]
        chunks = []
        async for chunk in agent.run_stream(messages, tool_callback=on_event):
            chunks.append(chunk)

        result = "".join(chunks)
        assert "Here is the content" in result

        # Verify tool events were emitted
        assert any(isinstance(e, ToolStart) for e in events)
        assert any(isinstance(e, ToolEnd) for e in events)

    @pytest.mark.asyncio
    async def test_run_stream_tool_not_found(self, mock_llm, mock_tool_registry):
        """Test run_stream when requested tool doesn't exist."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=3)

        call_count = 0

        async def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                tool_calls = [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "nonexistent_tool", "arguments": json.dumps({})},
                    }
                ]
                yield f"[TOOL_CALLS]{json.dumps(tool_calls)}"
            else:
                yield "Done"

        mock_llm.stream_chat_with_tools = mock_stream

        events = []

        def on_event(event):
            events.append(event)

        messages = [ChatMessage(role="user", content="Use bad tool")]
        chunks = []
        async for chunk in agent.run_stream(messages, tool_callback=on_event):
            chunks.append(chunk)

        # Should emit error events for missing tool
        error_ends = [e for e in events if isinstance(e, ToolEnd) and e.is_error]
        assert len(error_ends) == 1
        assert "not found" in error_ends[0].result

    @pytest.mark.asyncio
    async def test_run_stream_max_iterations(self, mock_llm, mock_tool_registry):
        """Test run_stream respects max_iterations."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=2)

        async def mock_stream(*args, **kwargs):
            # Always return tool call - infinite loop if not stopped
            tool_calls = [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "read", "arguments": json.dumps({"path": "test.txt"})},
                }
            ]
            yield f"[TOOL_CALLS]{json.dumps(tool_calls)}"

        mock_llm.stream_chat_with_tools = mock_stream

        messages = [ChatMessage(role="user", content="Keep calling")]
        chunks = []
        async for chunk in agent.run_stream(messages):
            chunks.append(chunk)

        # Should stop at max iterations without error
        assert len(chunks) == 0  # No content yielded since we always have tool calls
