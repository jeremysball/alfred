"""Tests for assign_session_id function (PRD #76)."""

from datetime import datetime, UTC, timedelta
from src.session import assign_session_id


def test_assign_session_id_creates_new_when_none():
    """Verify new session ID created when no current session exists."""
    new_time = datetime.now(UTC)
    
    session_id = assign_session_id(
        new_message_time=new_time,
        last_message_time=None,
        current_session_id=None,
    )
    
    assert session_id.startswith("sess_")
    assert len(session_id) == 17  # "sess_" + 12 hex chars
    assert session_id != ""


def test_assign_session_id_generates_unique_ids():
    """Verify multiple calls generate different session IDs."""
    new_time = datetime.now(UTC)
    
    session_id_1 = assign_session_id(
        new_message_time=new_time,
        last_message_time=None,
        current_session_id=None,
    )
    session_id_2 = assign_session_id(
        new_message_time=new_time,
        last_message_time=None,
        current_session_id=None,
    )
    
    assert session_id_1 != session_id_2
