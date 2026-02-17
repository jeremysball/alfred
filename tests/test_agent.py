"""Tests for the agent loop."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agent import Agent, ToolCall
from src.llm import ChatMessage, ChatResponse
from src.tools import ToolRegistry, Tool, clear_registry


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
        # arguments is a dict from validate_and_run_stream
        path = arguments.get('path', 'unknown')
        yield f"Contents of {path}"
    
    read_tool = MagicMock(spec=Tool)
    read_tool.name = "read"
    read_tool.validate_and_run_stream = mock_read_stream
    registry.register(read_tool)
    
    # Add mock bash tool
    async def mock_bash_stream(arguments):
        command = arguments.get('command', 'unknown')
        yield f"Output: {command}"
    
    bash_tool = MagicMock(spec=Tool)
    bash_tool.name = "bash"
    bash_tool.validate_and_run_stream = mock_bash_stream
    registry.register(bash_tool)
    
    return registry


class TestAgent:
    """Test suite for agent."""

    @pytest.mark.asyncio
    async def test_agent_no_tool_calls(self, mock_llm, mock_tool_registry):
        """Test agent with no tool calls - direct response."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=3)
        
        # Mock LLM to return text with no tool calls
        async def mock_stream(*args, **kwargs):
            yield "Hello! This is a direct response."
        
        mock_llm.stream_chat_with_tools = mock_stream
        
        messages = [ChatMessage(role="user", content="Hi")]
        result = await agent.run(messages)
        
        assert "Hello!" in result
        assert "direct response" in result

    @pytest.mark.asyncio
    async def test_agent_single_tool_call(self, mock_llm, mock_tool_registry):
        """Test agent with single tool call."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=3)
        
        call_count = 0
        
        async def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call - return tool call
                tool_calls = [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "read",
                        "arguments": json.dumps({"path": "test.txt"})
                    }
                }]
                yield f"[TOOL_CALLS]{json.dumps(tool_calls)}"
            else:
                # Second call - return final response
                yield "Here's what I found: Contents of test.txt"
        
        mock_llm.stream_chat_with_tools = mock_stream
        
        messages = [ChatMessage(role="user", content="Read test.txt")]
        result = await agent.run(messages)
        
        assert "Contents of test.txt" in result
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_agent_multiple_tool_calls(self, mock_llm, mock_tool_registry):
        """Test agent with multiple tool calls."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=3)
        
        call_count = 0
        
        async def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call - multiple tool calls
                tool_calls = [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read",
                            "arguments": json.dumps({"path": "file1.txt"})
                        }
                    },
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "read",
                            "arguments": json.dumps({"path": "file2.txt"})
                        }
                    }
                ]
                yield f"[TOOL_CALLS]{json.dumps(tool_calls)}"
            else:
                # Second call - final response
                yield "Found both files"
        
        mock_llm.stream_chat_with_tools = mock_stream
        
        messages = [ChatMessage(role="user", content="Read both files")]
        result = await agent.run(messages)
        
        assert "Found both files" in result
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_agent_tool_not_found(self, mock_llm, mock_tool_registry):
        """Test agent when tool is not found."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=3)
        
        call_count = 0
        
        async def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # Request a non-existent tool
                tool_calls = [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "nonexistent_tool",
                        "arguments": json.dumps({})
                    }
                }]
                yield f"[TOOL_CALLS]{json.dumps(tool_calls)}"
            else:
                yield "Tool not found"
        
        mock_llm.stream_chat_with_tools = mock_stream
        
        messages = [ChatMessage(role="user", content="Use nonexistent tool")]
        result = await agent.run(messages)
        
        assert "Tool not found" in result or "nonexistent" in result

    @pytest.mark.asyncio
    async def test_agent_max_iterations(self, mock_llm, mock_tool_registry):
        """Test agent respects max_iterations."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=2)
        
        async def mock_stream(*args, **kwargs):
            # Always return tool call - infinite loop if not stopped
            tool_calls = [{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "read",
                    "arguments": json.dumps({"path": "test.txt"})
                }
            }]
            yield f"[TOOL_CALLS]{json.dumps(tool_calls)}"
        
        mock_llm.stream_chat_with_tools = mock_stream
        
        messages = [ChatMessage(role="user", content="Keep calling")]
        result = await agent.run(messages)
        
        assert "Max iterations" in result

    @pytest.mark.asyncio
    async def test_agent_streaming(self, mock_llm, mock_tool_registry):
        """Test agent streaming."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=3)
        
        call_count = 0
        
        async def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                yield "Let me check that..."
                tool_calls = [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "read",
                        "arguments": json.dumps({"path": "test.txt"})
                    }
                }]
                yield f"[TOOL_CALLS]{json.dumps(tool_calls)}"
            else:
                yield "Here is the content"
        
        mock_llm.stream_chat_with_tools = mock_stream
        
        messages = [ChatMessage(role="user", content="Read file")]
        chunks = []
        async for chunk in agent.run_stream(messages):
            chunks.append(chunk)
        
        result = "".join(chunks)
        assert "Let me check" in result
        assert "[Executing: read]" in result
        assert "Contents of test.txt" in result
        assert "Here is the content" in result

    @pytest.mark.asyncio
    async def test_agent_with_system_prompt(self, mock_llm, mock_tool_registry):
        """Test agent with system prompt."""
        agent = Agent(mock_llm, mock_tool_registry, max_iterations=1)
        
        captured_messages = None
        
        async def mock_stream(messages, **kwargs):
            nonlocal captured_messages
            captured_messages = messages
            yield "Response"
        
        mock_llm.stream_chat_with_tools = mock_stream
        
        messages = [ChatMessage(role="user", content="Hello")]
        await agent.run(messages, system_prompt="You are a helpful assistant")
        
        # Check that system prompt was added
        assert captured_messages is not None
        assert any(m.role == "system" for m in captured_messages)
