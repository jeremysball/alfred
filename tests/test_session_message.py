"""Tests for Message dataclass session_id field (PRD #76)."""

from datetime import datetime, UTC
from src.session import Message, Role


def test_message_has_session_id_field():
    """Verify Message dataclass accepts and stores session_id."""
    message = Message(
        idx=0,
        role=Role.USER,
        content="Test message",
        session_id="sess_abc123",
    )
    assert message.session_id == "sess_abc123"


def test_message_session_id_defaults_to_empty_string():
    """Verify session_id defaults to empty string when not provided."""
    message = Message(
        idx=0,
        role=Role.USER,
        content="Test message",
    )
    assert message.session_id == ""


def test_message_with_all_fields_including_session_id():
    """Verify Message works with all fields including session_id."""
    message = Message(
        idx=1,
        role=Role.ASSISTANT,
        content="Response",
        timestamp=datetime.now(UTC),
        embedding=[0.1, 0.2, 0.3],
        input_tokens=10,
        output_tokens=20,
        session_id="sess_xyz789",
    )
    assert message.session_id == "sess_xyz789"
    assert message.idx == 1
    assert message.role == Role.ASSISTANT
