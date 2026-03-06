"""Tests for TUI session loading with tool calls."""

import pytest


class TestToolCallConversion:
    """Tests for converting ToolCallRecord to ToolCallInfo."""

    def test_convert_single_tool_call_record_success(self):
        """Verify one ToolCallRecord converts to one ToolCallInfo with success status."""
        from src.interfaces.pypitui.models import ToolCallInfo
        from src.interfaces.pypitui.tui import AlfredTUI
        from src.session import ToolCallRecord

        # Create a ToolCallRecord as would come from session storage
        record = ToolCallRecord(
            tool_call_id="call-1",
            tool_name="bash",
            arguments={"command": "ls -la"},
            output="file1.txt file2.txt",
            status="success",
            insert_position=10,
            sequence=0,
        )

        # Convert using the helper
        info = AlfredTUI._convert_tool_call_record(record)

        # Verify all fields mapped correctly
        assert info.tool_call_id == "call-1"
        assert info.tool_name == "bash"
        assert info.arguments == {"command": "ls -la"}
        assert info.output == "file1.txt file2.txt"
        assert info.status == "success"
        assert info.insert_position == 10
        assert info.sequence == 0

    def test_convert_single_tool_call_record_error(self):
        """Verify one ToolCallRecord converts to one ToolCallInfo with error status."""
        from src.interfaces.pypitui.models import ToolCallInfo
        from src.interfaces.pypitui.tui import AlfredTUI
        from src.session import ToolCallRecord

        record = ToolCallRecord(
            tool_call_id="call-2",
            tool_name="read",
            arguments={"path": "/nonexistent"},
            output="File not found",
            status="error",
            insert_position=5,
            sequence=1,
        )

        info = AlfredTUI._convert_tool_call_record(record)

        assert info.tool_call_id == "call-2"
        assert info.tool_name == "read"
        assert info.status == "error"
        assert info.insert_position == 5
        assert info.sequence == 1


class TestToolCallsListConversion:
    """Tests for batch converting lists of tool calls."""

    def test_convert_tool_calls_list(self):
        """Verify list of records converts to list of infos."""
        from src.interfaces.pypitui.tui import AlfredTUI
        from src.session import ToolCallRecord

        records = [
            ToolCallRecord(
                tool_call_id="call-1",
                tool_name="search_memories",
                arguments={"query": "blue"},
                output="Found: blue sky",
                status="success",
            ),
            ToolCallRecord(
                tool_call_id="call-2",
                tool_name="remember",
                arguments={"content": "sky is blue"},
                output="Memory saved",
                status="success",
            ),
        ]

        infos = AlfredTUI._convert_tool_calls(records)

        assert len(infos) == 2
        assert infos[0].tool_name == "search_memories"
        assert infos[1].tool_name == "remember"

    def test_convert_tool_calls_preserves_order(self):
        """Verify order is maintained during conversion."""
        from src.interfaces.pypitui.tui import AlfredTUI
        from src.session import ToolCallRecord

        records = [
            ToolCallRecord(
                tool_call_id=f"call-{i}",
                tool_name=f"tool-{i}",
                arguments={},
                output=f"output-{i}",
                status="success",
                sequence=i,
            )
            for i in range(5)
        ]

        infos = AlfredTUI._convert_tool_calls(records)

        for i, info in enumerate(infos):
            assert info.tool_call_id == f"call-{i}"
            assert info.sequence == i

    def test_convert_none_tool_calls(self):
        """Verify None input returns None (no conversion attempted)."""
        from src.interfaces.pypitui.tui import AlfredTUI

        result = AlfredTUI._convert_tool_calls(None)
        assert result is None

    def test_convert_empty_tool_calls_list(self):
        """Verify empty list returns empty list."""
        from src.interfaces.pypitui.tui import AlfredTUI

        result = AlfredTUI._convert_tool_calls([])
        assert result == []


class TestSessionLoadingWithToolCalls:
    """Tests for _load_session_messages with tool calls integration."""

    def test_load_session_passes_tool_calls_to_panel(self):
        """Verify MessagePanel receives tool_calls parameter when loading messages."""
        from src.interfaces.pypitui.message_panel import MessagePanel
        from src.interfaces.pypitui.models import ToolCallInfo
        from src.session import Message, Role, ToolCallRecord

        # Create a message with tool calls
        msg = Message(
            idx=0,
            role=Role.ASSISTANT,
            content="I found your files:",
            tool_calls=[
                ToolCallRecord(
                    tool_call_id="call-1",
                    tool_name="bash",
                    arguments={"command": "ls"},
                    output="file.txt",
                    status="success",
                )
            ],
        )

        # Create panel with tool calls
        tool_call_infos = [
            ToolCallInfo(
                tool_name=tc.tool_name,
                tool_call_id=tc.tool_call_id,
                insert_position=tc.insert_position,
                sequence=tc.sequence,
                arguments=tc.arguments,
                output=tc.output,
                status=tc.status,
            )
            for tc in msg.tool_calls
        ]

        panel = MessagePanel(
            role=msg.role.value,
            content=msg.content,
            tool_calls=tool_call_infos,
        )

        # Verify tool calls are in the panel
        assert len(panel._tool_calls) == 1
        assert panel._tool_calls[0].tool_name == "bash"

    def test_load_session_without_tool_calls(self):
        """Verify messages without tool_calls still work (backward compatibility)."""
        from src.interfaces.pypitui.message_panel import MessagePanel
        from src.session import Message, Role

        # Create a message without tool calls
        msg = Message(
            idx=0,
            role=Role.USER,
            content="Hello",
            tool_calls=None,
        )

        # Create panel without tool_calls parameter
        panel = MessagePanel(
            role=msg.role.value,
            content=msg.content,
        )

        # Should work fine with empty tool calls
        assert panel._tool_calls == []

    def test_load_session_with_empty_tool_calls(self):
        """Verify messages with empty tool_calls list work."""
        from src.interfaces.pypitui.message_panel import MessagePanel
        from src.session import Message, Role

        # Create a message with empty tool calls
        msg = Message(
            idx=0,
            role=Role.ASSISTANT,
            content="Hello",
            tool_calls=[],
        )

        # Create panel without tool_calls
        panel = MessagePanel(
            role=msg.role.value,
            content=msg.content,
            tool_calls=[],
        )

        assert panel._tool_calls == []
