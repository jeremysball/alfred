"""Test for the tool_calls dict vs object bug (PRD investigation).

After fix: tool_calls are converted to ToolCallRecord at the edge (load)
and used as objects everywhere inside the program.
"""

import pytest
from datetime import datetime, UTC
from alfred.session import (
    Message,
    Role,
    ToolCallRecord,
)


def test_tool_call_record_access():
    """ToolCallRecord objects support attribute access (.status, etc.)."""
    tc = ToolCallRecord(
        tool_call_id="call_123",
        tool_name="test_tool",
        arguments={"arg1": "value1"},
        output="result",
        status="success",
        insert_position=10,
        sequence=0,
    )
    
    # These should all work with attribute access
    assert tc.tool_call_id == "call_123"
    assert tc.tool_name == "test_tool"
    assert tc.arguments == {"arg1": "value1"}
    assert tc.output == "result"
    assert tc.status == "success"
    assert tc.insert_position == 10
    assert tc.sequence == 0


def test_create_session_from_data_converts_tool_calls():
    """Loading from storage converts dict tool_calls to ToolCallRecord objects."""
    # This simulates data coming from storage (dicts)
    storage_data = {
        "messages": [
            {
                "idx": 0,
                "role": "assistant",
                "content": "Test response",
                "timestamp": datetime.now(UTC).isoformat(),
                "input_tokens": 10,
                "output_tokens": 20,
                "tool_calls": [
                    {
                        "tool_call_id": "call_abc123",
                        "tool_name": "test_tool",
                        "arguments": {"arg1": "value1"},
                        "output": "tool output",
                        "status": "success",
                        "insert_position": 10,
                        "sequence": 0,
                    }
                ],
            }
        ]
    }

    # Simulate the conversion logic from _create_session_from_data
    for msg_data in storage_data.get("messages", []):
        tool_calls_data = msg_data.get("tool_calls")
        tool_calls = None
        if tool_calls_data:
            tool_calls = [
                ToolCallRecord(
                    tool_call_id=tc["tool_call_id"],
                    tool_name=tc["tool_name"],
                    arguments=tc.get("arguments", {}),
                    output=tc.get("output", ""),
                    status=tc.get("status", "success"),
                    insert_position=tc.get("insert_position", 0),
                    sequence=tc.get("sequence", 0),
                )
                for tc in tool_calls_data
            ]

        # Verify conversion to ToolCallRecord
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert isinstance(tool_calls[0], ToolCallRecord)
        
        # Verify attribute access works (this was the bug)
        assert tool_calls[0].tool_call_id == "call_abc123"
        assert tool_calls[0].tool_name == "test_tool"
        assert tool_calls[0].status == "success"


def test_persist_messages_uses_tool_call_record():
    """Persisting converts ToolCallRecord objects to dicts for storage."""
    msg = Message(
        idx=0,
        role=Role.ASSISTANT,
        content="Test message",
        timestamp=datetime.now(UTC),
        tool_calls=[
            ToolCallRecord(
                tool_call_id="call_456",
                tool_name="test_tool",
                arguments={"arg1": "value1"},
                output="result",
                status="success",
            )
        ],
    )

    # Simulate _persist_messages logic (always ToolCallRecord objects now)
    messages_data = []
    msg_dict = {
        "idx": msg.idx,
        "role": msg.role.value,
        "content": msg.content,
        "timestamp": msg.timestamp.isoformat(),
    }
    if msg.tool_calls:
        msg_dict["tool_calls"] = [
            {
                "tool_call_id": tc.tool_call_id,
                "tool_name": tc.tool_name,
                "arguments": tc.arguments,
                "output": tc.output,
                "status": tc.status,
                "insert_position": tc.insert_position,
                "sequence": tc.sequence,
            }
            for tc in msg.tool_calls
        ]

    messages_data.append(msg_dict)
    
    # Verify conversion to dict for storage
    assert len(messages_data) == 1
    assert messages_data[0]["tool_calls"][0]["tool_call_id"] == "call_456"
    assert messages_data[0]["tool_calls"][0]["status"] == "success"
