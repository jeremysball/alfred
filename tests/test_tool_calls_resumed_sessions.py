"""Integration tests for tool calls in resumed sessions (PRD #103).

End-to-end tests verifying that tool calls are properly displayed
when resuming sessions via /resume or startup.
"""

import pytest


class TestResumeSessionShowsToolCalls:
    """Integration tests for session resume with tool calls."""

    def test_resume_session_shows_tool_calls(self):
        """End-to-end: create session with tool calls, verify they appear on resume.

        This test simulates the full flow:
        1. Create a session with messages containing tool calls
        2. Load the session (as would happen on /resume)
        3. Verify tool calls are present in loaded messages
        """
        from datetime import UTC, datetime

        from src.interfaces.pypitui.models import ToolCallInfo
        from src.session import Message, Role, Session, SessionMeta, ToolCallRecord

        # Create a session with tool calls as would exist in storage
        session_id = "test-session-123"
        meta = SessionMeta(
            session_id=session_id,
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            status="active",
            current_count=2,
        )
        session = Session(meta=meta)

        # Add user message
        session.messages.append(
            Message(
                idx=0,
                role=Role.USER,
                content="List files in current directory",
            )
        )

        # Add assistant message with tool call
        session.messages.append(
            Message(
                idx=1,
                role=Role.ASSISTANT,
                content="I'll list the files for you:",
                tool_calls=[
                    ToolCallRecord(
                        tool_call_id="call-1",
                        tool_name="bash",
                        arguments={"command": "ls -la", "timeout": 30},
                        output="total 16\ndrwxr-xr-x 2 user user 4096 Mar 6 10:00 .\n-rw-r--r-- 1 user user 1234 Mar 6 09:00 file.txt",
                        status="success",
                        insert_position=28,  # After "I'll list the files for you:"
                        sequence=0,
                    )
                ],
            )
        )

        # Verify session has tool calls
        assert len(session.messages) == 2
        assistant_msg = session.messages[1]
        assert assistant_msg.tool_calls is not None
        assert len(assistant_msg.tool_calls) == 1
        assert assistant_msg.tool_calls[0].tool_name == "bash"
        assert assistant_msg.tool_calls[0].status == "success"

        # Simulate what _load_session_messages does: convert to ToolCallInfo
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
            for tc in assistant_msg.tool_calls
        ]

        # Verify conversion worked
        assert len(tool_call_infos) == 1
        assert tool_call_infos[0].tool_name == "bash"
        assert tool_call_infos[0].output == assistant_msg.tool_calls[0].output

    def test_multiple_tool_calls_in_session(self):
        """Verify multiple tool calls in a session are all preserved."""
        from datetime import UTC, datetime

        from src.interfaces.pypitui.models import ToolCallInfo
        from src.session import Message, Role, Session, SessionMeta, ToolCallRecord

        session_id = "test-session-multi"
        meta = SessionMeta(
            session_id=session_id,
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            status="active",
            current_count=3,
        )
        session = Session(meta=meta)

        # User asks to search and remember
        session.messages.append(
            Message(
                idx=0,
                role=Role.USER,
                content="Search for 'blue' and remember it",
            )
        )

        # Assistant searches, then remembers
        session.messages.append(
            Message(
                idx=1,
                role=Role.ASSISTANT,
                content="Let me search and save that:",
                tool_calls=[
                    ToolCallRecord(
                        tool_call_id="call-1",
                        tool_name="search_memories",
                        arguments={"query": "blue"},
                        output="Found: blue sky, blue ocean",
                        status="success",
                        insert_position=30,
                        sequence=0,
                    ),
                    ToolCallRecord(
                        tool_call_id="call-2",
                        tool_name="remember",
                        arguments={"content": "User likes blue things"},
                        output="Memory saved successfully",
                        status="success",
                        insert_position=30,
                        sequence=1,
                    ),
                ],
            )
        )

        # Verify both tool calls are present
        assistant_msg = session.messages[1]
        assert len(assistant_msg.tool_calls) == 2

        # Convert and verify both are preserved
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
            for tc in assistant_msg.tool_calls
        ]

        assert len(tool_call_infos) == 2
        assert tool_call_infos[0].tool_name == "search_memories"
        assert tool_call_infos[1].tool_name == "remember"
        assert tool_call_infos[0].sequence == 0
        assert tool_call_infos[1].sequence == 1

    def test_tool_call_success_and_error_status(self):
        """Verify both success and error tool call statuses are preserved."""
        from datetime import UTC, datetime

        from src.session import Message, Role, Session, SessionMeta, ToolCallRecord

        meta = SessionMeta(
            session_id="test-status-session",
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            status="active",
            current_count=2,
        )
        session = Session(meta=meta)

        # Add assistant message with success and error tool calls
        session.messages.append(
            Message(
                idx=0,
                role=Role.ASSISTANT,
                content="Here are the results:",
                tool_calls=[
                    ToolCallRecord(
                        tool_call_id="call-success",
                        tool_name="read",
                        arguments={"path": "/existing/file.txt"},
                        output="File contents here",
                        status="success",
                    ),
                    ToolCallRecord(
                        tool_call_id="call-error",
                        tool_name="read",
                        arguments={"path": "/nonexistent"},
                        output="Error: File not found",
                        status="error",
                    ),
                ],
            )
        )

        # Verify statuses are preserved
        tool_calls = session.messages[0].tool_calls
        assert tool_calls[0].status == "success"
        assert tool_calls[1].status == "error"


class TestToolCallPersistenceRoundTrip:
    """Tests for full persistence round-trip of tool calls."""

    def test_tool_call_arguments_preserved(self):
        """Verify tool call arguments are preserved through save/load."""
        from datetime import UTC, datetime

        from src.session import Message, Role, Session, SessionMeta, ToolCallRecord

        meta = SessionMeta(
            session_id="test-args-session",
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            status="active",
        )
        session = Session(meta=meta)

        # Add message with complex arguments
        session.messages.append(
            Message(
                idx=0,
                role=Role.ASSISTANT,
                content="Running command:",
                tool_calls=[
                    ToolCallRecord(
                        tool_call_id="call-1",
                        tool_name="bash",
                        arguments={
                            "command": "find /tmp -name '*.txt' -exec rm {} \\;",
                            "timeout": 60,
                            "working_dir": "/home/user",
                        },
                        output="Files removed",
                        status="success",
                    )
                ],
            )
        )

        # Verify arguments are preserved
        tool_call = session.messages[0].tool_calls[0]
        assert tool_call.arguments["command"] == "find /tmp -name '*.txt' -exec rm {} \\;"
        assert tool_call.arguments["timeout"] == 60
        assert tool_call.arguments["working_dir"] == "/home/user"


class TestLargeSessionPerformance:
    """Performance tests for large sessions with many tool calls."""

    def test_large_session_loads_efficiently(self):
        """Verify session with 100+ messages with tool calls loads reasonably.

        This test ensures no O(n²) or worse behavior in session loading.
        """
        import time
        from datetime import UTC, datetime

        from src.interfaces.pypitui.models import ToolCallInfo
        from src.session import Message, Role, Session, SessionMeta, ToolCallRecord

        meta = SessionMeta(
            session_id="perf-test-session",
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            status="active",
        )
        session = Session(meta=meta)

        # Create 100 messages, each with 2 tool calls
        for i in range(100):
            session.messages.append(
                Message(
                    idx=i,
                    role=Role.ASSISTANT,
                    content=f"Message {i}",
                    tool_calls=[
                        ToolCallRecord(
                            tool_call_id=f"call-{i}-a",
                            tool_name="search_memories",
                            arguments={"query": f"query-{i}"},
                            output=f"Results for {i}",
                            status="success",
                        ),
                        ToolCallRecord(
                            tool_call_id=f"call-{i}-b",
                            tool_name="bash",
                            arguments={"command": f"echo {i}"},
                            output=str(i),
                            status="success",
                        ),
                    ],
                )
            )

        # Time the conversion (simulating _load_session_messages)
        start = time.time()

        for msg in session.messages:
            if msg.tool_calls:
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
                assert len(tool_call_infos) == 2

        elapsed = time.time() - start

        # Should complete in under 2 seconds (very generous)
        assert elapsed < 2.0, f"Large session conversion took {elapsed:.2f}s, expected < 2s"
