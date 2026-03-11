"""Test that tool calls are loaded when resuming a session (PRD #101)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from alfred.interfaces.pypitui.message_panel import MessagePanel
from alfred.interfaces.pypitui.models import ToolCallInfo
from alfred.session import Message, Role, ToolCallRecord


class TestToolCallsLoadWithSession:
    """Test that tool calls appear when loading session messages."""

    def test_message_panel_restores_tool_calls(self):
        """Test that MessagePanel can restore tool calls from ToolCallInfo objects."""
        panel = MessagePanel(role="assistant", content="Let me check that file.")

        # Create tool call info objects as they would be stored
        tool_infos = [
            ToolCallInfo(
                tool_name="read",
                tool_call_id="call_1",
                output="File content here",
                status="success",
                insert_position=21,
                sequence=0,
                arguments={"path": "/tmp/test.txt"},
            ),
            ToolCallInfo(
                tool_name="bash",
                tool_call_id="call_2",
                output="output\nlines",
                status="success",
                insert_position=21,
                sequence=1,
                arguments={"command": "ls -la"},
            ),
        ]

        # Restore tool calls
        panel.restore_tool_calls(tool_infos)

        # Verify tool calls are restored
        assert len(panel.tool_calls) == 2
        assert panel.tool_calls[0].tool_name == "read"
        assert panel.tool_calls[1].tool_name == "bash"
        assert panel.tool_calls[0].status == "success"
        assert panel.tool_calls[0].output == "File content here"

    def test_message_panel_restores_tool_calls_from_tool_call_records(self):
        """Test restoring tool calls from session ToolCallRecord objects."""
        panel = MessagePanel(role="assistant", content="Let me check.")

        # ToolCallRecord as stored in session
        tool_records = [
            ToolCallRecord(
                tool_call_id="call_abc",
                tool_name="bash",
                arguments={"command": "pwd"},
                output="/home/user",
                status="success",
                insert_position=13,
                sequence=0,
            )
        ]

        # Restore from records
        panel.restore_tool_calls_from_records(tool_records)

        # Verify
        assert len(panel.tool_calls) == 1
        assert panel.tool_calls[0].tool_name == "bash"
        assert panel.tool_calls[0].status == "success"
        assert panel.tool_calls[0].output == "/home/user"
        assert panel.tool_calls[0].arguments == {"command": "pwd"}

    @pytest.mark.asyncio
    async def test_tui_loads_session_messages_with_tool_calls(self):
        """Test that TUI loads tool calls when loading session messages."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        # Create mock session with messages containing tool calls
        mock_session = MagicMock()
        mock_session.messages = [
            Message(
                idx=0,
                role=Role.USER,
                content="Check this file",
                timestamp=datetime.now(UTC),
            ),
            Message(
                idx=1,
                role=Role.ASSISTANT,
                content="I'll read the file for you.",
                timestamp=datetime.now(UTC),
                tool_calls=[
                    ToolCallRecord(
                        tool_call_id="call_1",
                        tool_name="read",
                        arguments={"path": "/tmp/test.txt"},
                        output="File contents here",
                        status="success",
                        insert_position=28,
                        sequence=0,
                    )
                ],
            ),
        ]

        # Mock Alfred and config
        mock_alfred = MagicMock()
        mock_alfred.config.use_markdown_rendering = True
        mock_alfred.core.session_manager.has_active_session.return_value = True
        mock_alfred.core.session_manager.get_current_cli_session_async = AsyncMock(
            return_value=mock_session
        )
        # Mock token tracker to avoid MagicMock comparison errors
        mock_alfred.token_tracker.usage.input_tokens = 100
        mock_alfred.token_tracker.usage.output_tokens = 50
        mock_alfred.token_tracker.usage.cache_read_tokens = 0
        mock_alfred.token_tracker.usage.reasoning_tokens = 0
        mock_alfred.token_tracker.context_tokens = 200
        mock_alfred.model_name = "test-model"

        # Create TUI with mocked terminal
        mock_terminal = MagicMock()
        mock_terminal.get_size.return_value = (80, 24)

        tui = AlfredTUI(alfred=mock_alfred, terminal=mock_terminal)

        # Load session messages
        await tui._load_session_messages()

        # Verify conversation has 2 panels (user + assistant)
        assert len(tui.conversation.children) == 2

        # Verify assistant message panel has tool calls
        assistant_panel = tui.conversation.children[1]
        assert isinstance(assistant_panel, MessagePanel)
        assert len(assistant_panel.tool_calls) == 1
        assert assistant_panel.tool_calls[0].tool_name == "read"
        assert assistant_panel.tool_calls[0].status == "success"

    def test_empty_tool_calls_list_handled(self):
        """Test that empty tool calls list is handled gracefully."""
        panel = MessagePanel(role="assistant", content="No tools used.")

        # Restore empty list
        panel.restore_tool_calls([])

        # Should have no tool calls
        assert len(panel.tool_calls) == 0

    def test_none_tool_calls_skipped(self):
        """Test that None tool_calls is handled gracefully."""
        panel = MessagePanel(role="assistant", content="No tools used.")

        # Restore None
        panel.restore_tool_calls(None)  # type: ignore[arg-type]

        # Should have no tool calls
        assert len(panel.tool_calls) == 0
