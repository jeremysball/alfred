"""Tests for tool call persistence (PRD #101 Milestone 1)."""

import json
from datetime import UTC, datetime

import pytest

from src.session import Message, Role, ToolCallRecord
from src.session_storage import SessionStorage


class TestToolCallRecord:
    """Test ToolCallRecord dataclass."""

    def test_creation(self):
        """Test basic ToolCallRecord creation."""
        record = ToolCallRecord(
            tool_call_id="call_abc123",
            tool_name="bash",
            arguments={"command": "ls /tmp"},
            output="a.txt\nb.txt",
            status="success",
            insert_position=42,
            sequence=0,
        )
        assert record.tool_call_id == "call_abc123"
        assert record.tool_name == "bash"
        assert record.arguments == {"command": "ls /tmp"}
        assert record.output == "a.txt\nb.txt"
        assert record.status == "success"
        assert record.insert_position == 42
        assert record.sequence == 0

    def test_defaults(self):
        """Test default values for optional fields."""
        record = ToolCallRecord(
            tool_call_id="call_xyz789",
            tool_name="read",
            arguments={"path": "/tmp/test.txt"},
            output="file contents",
            status="error",
        )
        assert record.insert_position == 0
        assert record.sequence == 0

    def test_error_status(self):
        """Test error status."""
        record = ToolCallRecord(
            tool_call_id="call_err001",
            tool_name="bash",
            arguments={"command": "invalid"},
            output="Error: command not found",
            status="error",
        )
        assert record.status == "error"


class TestMessageWithToolCalls:
    """Test Message with tool_calls field."""

    def test_message_without_tool_calls(self):
        """Test message without tool calls (backward compatibility)."""
        msg = Message(
            idx=0,
            role=Role.USER,
            content="Hello",
        )
        assert msg.tool_calls is None

    def test_message_with_tool_calls(self):
        """Test message with tool calls."""
        tool_call = ToolCallRecord(
            tool_call_id="call_123",
            tool_name="bash",
            arguments={"command": "ls"},
            output="file1\nfile2",
            status="success",
            insert_position=10,
            sequence=0,
        )
        msg = Message(
            idx=1,
            role=Role.ASSISTANT,
            content="Let me check",
            tool_calls=[tool_call],
        )
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].tool_name == "bash"
        assert msg.tool_calls[0].insert_position == 10

    def test_message_with_multiple_tool_calls(self):
        """Test message with multiple tool calls."""
        tool_calls = [
            ToolCallRecord(
                tool_call_id="call_1",
                tool_name="read",
                arguments={"path": "/tmp/a.txt"},
                output="content a",
                status="success",
                insert_position=15,
                sequence=0,
            ),
            ToolCallRecord(
                tool_call_id="call_2",
                tool_name="read",
                arguments={"path": "/tmp/b.txt"},
                output="content b",
                status="success",
                insert_position=15,
                sequence=1,
            ),
        ]
        msg = Message(
            idx=1,
            role=Role.ASSISTANT,
            content="Reading files",
            tool_calls=tool_calls,
        )
        assert len(msg.tool_calls) == 2
        assert msg.tool_calls[0].sequence == 0
        assert msg.tool_calls[1].sequence == 1


class TestSessionStorageToolCalls:
    """Test SessionStorage serialization with tool calls."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create a temporary SessionStorage."""
        # Mock embedder that doesn't actually embed
        class MockEmbedder:
            async def embed(self, text):
                return [0.1, 0.2, 0.3]

        storage = SessionStorage(MockEmbedder(), data_dir=tmp_path)
        return storage

    @pytest.mark.asyncio
    async def test_append_message_with_tool_calls(self, temp_storage):
        """Test appending message with tool calls to current.jsonl."""
        # Create session
        meta = temp_storage.create_session("test_session")

        # Create message with tool calls
        tool_call = ToolCallRecord(
            tool_call_id="call_test123",
            tool_name="bash",
            arguments={"command": "echo hello"},
            output="hello",
            status="success",
            insert_position=5,
            sequence=0,
        )
        message = Message(
            idx=0,
            role=Role.ASSISTANT,
            content="Running command",
            timestamp=datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC),
            tool_calls=[tool_call],
        )

        # Append message
        await temp_storage.append_message("test_session", message)

        # Verify file contents
        messages_path = temp_storage.sessions_dir / "test_session" / "current.jsonl"
        assert messages_path.exists()

        with open(messages_path) as f:
            data = json.loads(f.readline())

        assert data["idx"] == 0
        assert data["role"] == "assistant"
        assert data["content"] == "Running command"
        assert "tool_calls" in data
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["tool_call_id"] == "call_test123"
        assert data["tool_calls"][0]["tool_name"] == "bash"
        assert data["tool_calls"][0]["arguments"] == {"command": "echo hello"}
        assert data["tool_calls"][0]["output"] == "hello"
        assert data["tool_calls"][0]["status"] == "success"
        assert data["tool_calls"][0]["insert_position"] == 5
        assert data["tool_calls"][0]["sequence"] == 0

    def test_load_messages_with_tool_calls(self, temp_storage):
        """Test loading messages with tool calls."""
        # Create session and write raw JSON
        meta = temp_storage.create_session("test_session2")

        raw_message = {
            "idx": 1,
            "role": "assistant",
            "content": "Found files",
            "timestamp": datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC).isoformat(),
            "tool_calls": [
                {
                    "tool_call_id": "call_load456",
                    "tool_name": "bash",
                    "arguments": {"command": "ls /tmp"},
                    "output": "a.txt\nb.txt",
                    "status": "success",
                    "insert_position": 0,
                    "sequence": 0,
                }
            ],
        }

        messages_path = temp_storage.sessions_dir / "test_session2" / "current.jsonl"
        with open(messages_path, "w") as f:
            f.write(json.dumps(raw_message) + "\n")

        # Load messages
        messages = temp_storage.load_messages("test_session2")

        assert len(messages) == 1
        msg = messages[0]
        assert msg.idx == 1
        assert msg.role == Role.ASSISTANT
        assert msg.content == "Found files"
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1

        tc = msg.tool_calls[0]
        assert tc.tool_call_id == "call_load456"
        assert tc.tool_name == "bash"
        assert tc.arguments == {"command": "ls /tmp"}
        assert tc.output == "a.txt\nb.txt"
        assert tc.status == "success"
        assert tc.insert_position == 0
        assert tc.sequence == 0

    def test_backward_compatibility_no_tool_calls(self, temp_storage):
        """Test loading old messages without tool_calls field."""
        # Create session and write legacy message (no tool_calls)
        meta = temp_storage.create_session("legacy_session")

        legacy_message = {
            "idx": 0,
            "role": "user",
            "content": "Hello",
            "timestamp": datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC).isoformat(),
            # No tool_calls field
        }

        messages_path = temp_storage.sessions_dir / "legacy_session" / "current.jsonl"
        with open(messages_path, "w") as f:
            f.write(json.dumps(legacy_message) + "\n")

        # Load should not fail
        messages = temp_storage.load_messages("legacy_session")

        assert len(messages) == 1
        msg = messages[0]
        assert msg.idx == 0
        assert msg.role == Role.USER
        assert msg.content == "Hello"
        assert msg.tool_calls is None  # Should default to None

    @pytest.mark.asyncio
    async def test_multiple_messages_mixed(self, temp_storage):
        """Test session with mix of messages with and without tool calls."""
        meta = temp_storage.create_session("mixed_session")

        # User message (no tool calls)
        user_msg = Message(
            idx=0,
            role=Role.USER,
            content="What files?",
            timestamp=datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC),
        )

        # Assistant message with tool calls
        tool_call = ToolCallRecord(
            tool_call_id="call_multi",
            tool_name="bash",
            arguments={"command": "ls -la"},
            output="total 0\ndrwx...",
            status="success",
            insert_position=8,
            sequence=0,
        )
        assistant_msg = Message(
            idx=1,
            role=Role.ASSISTANT,
            content="Checking now",
            timestamp=datetime(2026, 3, 2, 12, 0, 1, tzinfo=UTC),
            tool_calls=[tool_call],
        )

        await temp_storage.append_message("mixed_session", user_msg)
        await temp_storage.append_message("mixed_session", assistant_msg)

        # Load and verify
        messages = temp_storage.load_messages("mixed_session")

        assert len(messages) == 2
        assert messages[0].tool_calls is None
        assert messages[1].tool_calls is not None
        assert len(messages[1].tool_calls) == 1

    def test_load_full_session_with_tool_calls(self, temp_storage):
        """Test load_session returns Session with tool_calls."""
        # Create session with raw data
        meta = temp_storage.create_session("full_session")

        raw_data = {
            "idx": 0,
            "role": "assistant",
            "content": "Tool result",
            "timestamp": datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC).isoformat(),
            "tool_calls": [
                {
                    "tool_call_id": "call_full",
                    "tool_name": "read",
                    "arguments": {"path": "test.txt"},
                    "output": "file content here",
                    "status": "success",
                    "insert_position": 0,
                    "sequence": 0,
                }
            ],
        }

        messages_path = temp_storage.sessions_dir / "full_session" / "current.jsonl"
        with open(messages_path, "w") as f:
            f.write(json.dumps(raw_data) + "\n")

        # Load full session
        session = temp_storage.load_session("full_session")

        assert session is not None
        assert session.meta.session_id == "full_session"
        assert len(session.messages) == 1
        assert session.messages[0].tool_calls is not None
