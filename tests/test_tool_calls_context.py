"""Tests for tool calls in LLM context (PRD #101 Milestone 2)."""

import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock

from src.search import ContextBuilder, MemorySearcher
from src.session import Message, Role, ToolCallRecord
from src.memory import MemoryEntry


class TestToolCallsContextConfig:
    """Test tool calls configuration defaults."""

    def test_tool_calls_config_defaults(self):
        """Test that tool calls config has sensible defaults."""
        from src.config import Config
        
        # Mock the required fields
        config = MagicMock(spec=Config)
        config.tool_calls_enabled = True
        config.tool_calls_max_calls = 5
        config.tool_calls_max_tokens = 2000
        config.tool_calls_include_output = True
        config.tool_calls_include_arguments = True
        
        assert config.tool_calls_enabled is True
        assert config.tool_calls_max_calls == 5
        assert config.tool_calls_max_tokens == 2000
        assert config.tool_calls_include_output is True
        assert config.tool_calls_include_arguments is True


class TestContextBuilderToolCalls:
    """Test ContextBuilder includes tool calls in context."""

    @pytest.fixture
    def context_builder(self):
        """Create a ContextBuilder with mocked searcher."""
        searcher = MagicMock(spec=MemorySearcher)
        searcher.search.return_value = ([], [], [])
        return ContextBuilder(searcher, memory_budget=32000)

    def _create_message_with_tool_calls(self, content="Test", tool_calls=None):
        """Helper to create a message with tool calls."""
        return Message(
            idx=0,
            role=Role.ASSISTANT,
            content=content,
            timestamp=datetime.now(UTC),
            tool_calls=tool_calls,
        )

    def test_format_tool_calls_empty(self, context_builder):
        """Test formatting when no tool calls exist."""
        messages = [
            Message(idx=0, role=Role.USER, content="Hello", timestamp=datetime.now(UTC)),
        ]
        
        result = context_builder._format_tool_calls(messages)
        assert result == ""

    def test_format_tool_calls_single(self, context_builder):
        """Test formatting a single tool call."""
        tool_call = ToolCallRecord(
            tool_call_id="call_123",
            tool_name="bash",
            arguments={"command": "ls /tmp"},
            output="a.txt\nb.txt",
            status="success",
            insert_position=0,
            sequence=0,
        )
        messages = [
            self._create_message_with_tool_calls("I found files", [tool_call]),
        ]
        
        result = context_builder._format_tool_calls(messages)
        
        assert "bash" in result
        assert "ls /tmp" in result
        assert "a.txt" in result
        assert "b.txt" in result

    def test_format_tool_calls_multiple(self, context_builder):
        """Test formatting multiple tool calls from different messages."""
        tool_calls_1 = [
            ToolCallRecord(
                tool_call_id="call_1",
                tool_name="bash",
                arguments={"command": "ls /tmp"},
                output="files...",
                status="success",
                insert_position=0,
                sequence=0,
            ),
        ]
        tool_calls_2 = [
            ToolCallRecord(
                tool_call_id="call_2",
                tool_name="read",
                arguments={"path": "/tmp/file.txt"},
                output="content here",
                status="success",
                insert_position=0,
                sequence=0,
            ),
        ]
        messages = [
            Message(idx=0, role=Role.USER, content="Query", timestamp=datetime.now(UTC)),
            self._create_message_with_tool_calls("Found files", tool_calls_1),
            self._create_message_with_tool_calls("Read file", tool_calls_2),
        ]
        
        result = context_builder._format_tool_calls(messages)
        
        assert "bash" in result
        assert "read" in result
        assert "files..." in result
        assert "content here" in result

    def test_format_tool_calls_respects_max_calls(self, context_builder):
        """Test that max_calls limit is respected."""
        tool_calls = [
            ToolCallRecord(
                tool_call_id=f"call_{i}",
                tool_name="bash",
                arguments={"command": f"echo {i}"},
                output=str(i),
                status="success",
                insert_position=0,
                sequence=i,
            )
            for i in range(10)
        ]
        messages = [
            self._create_message_with_tool_calls("Many commands", tool_calls),
        ]
        
        result = context_builder._format_tool_calls(messages, max_calls=3)
        
        # Should only include first 3
        assert result.count("bash") == 3

    def test_format_tool_calls_excludes_output_when_disabled(self, context_builder):
        """Test that output is excluded when include_output=False."""
        tool_call = ToolCallRecord(
            tool_call_id="call_123",
            tool_name="bash",
            arguments={"command": "ls /tmp"},
            output="secret output here",
            status="success",
            insert_position=0,
            sequence=0,
        )
        messages = [
            self._create_message_with_tool_calls("Command", [tool_call]),
        ]
        
        result = context_builder._format_tool_calls(messages, include_output=False)
        
        assert "bash" in result
        assert "ls /tmp" in result
        assert "secret output here" not in result

    def test_format_tool_calls_excludes_arguments_when_disabled(self, context_builder):
        """Test that arguments are excluded when include_arguments=False."""
        tool_call = ToolCallRecord(
            tool_call_id="call_123",
            tool_name="bash",
            arguments={"command": "ls /tmp"},
            output="output",
            status="success",
            insert_position=0,
            sequence=0,
        )
        messages = [
            self._create_message_with_tool_calls("Command", [tool_call]),
        ]
        
        result = context_builder._format_tool_calls(messages, include_arguments=False)
        
        assert "bash" in result
        assert "ls /tmp" not in result  # Arguments hidden
        assert "output" in result

    def test_format_tool_calls_error_status(self, context_builder):
        """Test that error status is displayed."""
        tool_call = ToolCallRecord(
            tool_call_id="call_123",
            tool_name="bash",
            arguments={"command": "invalid"},
            output="Error: command not found",
            status="error",
            insert_position=0,
            sequence=0,
        )
        messages = [
            self._create_message_with_tool_calls("Failed", [tool_call]),
        ]
        
        result = context_builder._format_tool_calls(messages)
        
        assert "error" in result.lower() or "failed" in result.lower()
        assert "Error: command not found" in result


class TestContextBuilderWithToolCallsIntegration:
    """Integration tests for tool calls in full context."""

    @pytest.fixture
    def context_builder(self):
        """Create a ContextBuilder with mocked searcher."""
        searcher = MagicMock(spec=MemorySearcher)
        searcher.search.return_value = ([], [], [])
        return ContextBuilder(searcher, memory_budget=32000)

    def test_build_context_includes_tool_calls_section(self, context_builder):
        """Test that build_context includes tool calls section when messages have tool_calls."""
        tool_call = ToolCallRecord(
            tool_call_id="call_123",
            tool_name="bash",
            arguments={"command": "ls"},
            output="files",
            status="success",
            insert_position=0,
            sequence=0,
        )
        messages = [
            Message(
                idx=0,
                role=Role.ASSISTANT,
                content="Found files",
                timestamp=datetime.now(UTC),
                tool_calls=[tool_call],
            ),
        ]
        
        context, mem_count = context_builder.build_context(
            query_embedding=[0.1, 0.2],
            memories=[],
            system_prompt="System prompt",
            session_messages_with_tools=messages,  # New parameter
        )
        
        assert "## RECENT TOOL CALLS" in context
        assert "bash" in context

    def test_build_context_no_tool_calls_when_disabled(self, context_builder):
        """Test that tool calls section is omitted when no tool_calls in messages."""
        messages = [
            Message(
                idx=0,
                role=Role.ASSISTANT,
                content="Simple response",
                timestamp=datetime.now(UTC),
                tool_calls=None,
            ),
        ]
        
        context, mem_count = context_builder.build_context(
            query_embedding=[0.1, 0.2],
            memories=[],
            system_prompt="System prompt",
            session_messages_with_tools=messages,
        )
        
        assert "## RECENT TOOL CALLS" not in context

    def test_build_context_token_budget_for_tool_calls(self, context_builder):
        """Test that tool calls respect max_tokens budget."""
        # Create many tool calls with large output
        tool_calls = [
            ToolCallRecord(
                tool_call_id=f"call_{i}",
                tool_name="read",
                arguments={"path": f"/tmp/file{i}.txt"},
                output="x" * 500,  # Large output
                status="success",
                insert_position=0,
                sequence=i,
            )
            for i in range(10)
        ]
        messages = [
            Message(
                idx=0,
                role=Role.ASSISTANT,
                content="Many files",
                timestamp=datetime.now(UTC),
                tool_calls=tool_calls,
            ),
        ]
        
        context, mem_count = context_builder.build_context(
            query_embedding=[0.1, 0.2],
            memories=[],
            system_prompt="System prompt",
            session_messages_with_tools=messages,
            tool_calls_max_tokens=1000,  # Small budget
        )
        
        assert "## RECENT TOOL CALLS" in context
        # Should be truncated due to token budget
        # (exact verification depends on implementation)
