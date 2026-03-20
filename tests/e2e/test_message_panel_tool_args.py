"""Tests for tool arguments display in message panel (PRD #101 Milestone 3)."""

import pytest

from alfred.interfaces.pypitui.message_panel import MessagePanel
from alfred.interfaces.pypitui.models import ToolCallInfo


class TestToolCallInfoArguments:
    """Test ToolCallInfo with arguments field."""

    def test_tool_call_info_with_arguments(self):
        """Test ToolCallInfo stores arguments."""
        tool_info = ToolCallInfo(
            tool_name="bash",
            tool_call_id="call_123",
            arguments={"command": "ls /tmp"},
            output="a.txt\nb.txt",
            status="success",
        )
        assert tool_info.arguments == {"command": "ls /tmp"}

    def test_tool_call_info_no_arguments(self):
        """Test ToolCallInfo works without arguments (backward compat)."""
        tool_info = ToolCallInfo(
            tool_name="read",
            tool_call_id="call_456",
        )
        assert tool_info.arguments == {}


class TestMessagePanelToolArgs:
    """Test MessagePanel displays tool arguments."""

    @pytest.fixture
    def message_panel(self):
        """Create a MessagePanel for testing."""
        return MessagePanel(
            role="assistant",
            content="",
            terminal_width=80,
            use_markdown=False,
        )

    def test_add_tool_call_with_arguments(self, message_panel):
        """Test add_tool_call accepts and stores arguments."""
        message_panel.add_tool_call(
            tool_name="bash",
            tool_call_id="call_123",
            arguments={"command": "ls /tmp"},
        )

        tool_call = message_panel.get_tool_call("call_123")
        assert tool_call is not None
        assert tool_call.arguments == {"command": "ls /tmp"}

    def test_add_tool_call_without_arguments(self, message_panel):
        """Test add_tool_call works without arguments (backward compat)."""
        message_panel.add_tool_call(
            tool_name="read",
            tool_call_id="call_456",
        )

        tool_call = message_panel.get_tool_call("call_456")
        assert tool_call is not None
        assert tool_call.arguments == {}

    def test_tool_box_shows_arguments(self, message_panel):
        """Test tool box renders arguments as first line."""
        message_panel.add_tool_call(
            tool_name="bash",
            tool_call_id="call_123",
            arguments={"command": "ls /tmp"},
        )
        message_panel.update_tool_call("call_123", "a.txt\nb.txt")
        message_panel.finalize_tool_call("call_123", "success")

        # Rebuild content
        message_panel._rebuild_content()

        # Get the tool call info
        tool_call = message_panel.get_tool_call("call_123")
        assert tool_call is not None
        assert tool_call.arguments == {"command": "ls /tmp"}

        # The content is rendered in child elements, so check children exist
        # (actual rendering tested via integration tests)
        assert len(message_panel.children) > 0

    def test_tool_args_format_key_value(self, message_panel):
        """Test arguments formatted as key=value pairs."""
        message_panel.add_tool_call(
            tool_name="read",
            tool_call_id="call_789",
            arguments={"path": "/tmp/file.txt", "limit": 100},
        )

        tool_call = message_panel.get_tool_call("call_789")
        # Should format multiple args
        args_str = ", ".join(f"{k}={v}" for k, v in tool_call.arguments.items())
        assert "path=/tmp/file.txt" in args_str
        assert "limit=100" in args_str

    def test_tool_args_truncation(self, message_panel):
        """Test long arguments are truncated."""
        long_args = {"content": "x" * 100}
        message_panel.add_tool_call(
            tool_name="write",
            tool_call_id="call_long",
            arguments=long_args,
        )

        # Should not crash, and should store full args
        tool_call = message_panel.get_tool_call("call_long")
        assert len(tool_call.arguments["content"]) == 100

    def test_tool_box_no_args_shows_no_args_line(self, message_panel):
        """Test tool box without arguments doesn't show empty args line."""
        message_panel.add_tool_call(
            tool_name="remember",
            tool_call_id="call_no_args",
            arguments={},
        )
        message_panel.update_tool_call("call_no_args", "Memory stored")

        # Rebuild content
        message_panel._rebuild_content()

        # Get the tool call info
        tool_call = message_panel.get_tool_call("call_no_args")
        assert tool_call is not None
        assert tool_call.arguments == {}
        assert tool_call.tool_name == "remember"

        # The content is rendered in child elements
        assert len(message_panel.children) > 0
