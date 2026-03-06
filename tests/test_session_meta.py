"""Tests for SessionMeta dataclass extension (PRD #76)."""

from datetime import datetime, UTC
from src.session import SessionMeta


def test_session_meta_tracks_first_message_time():
    """Verify SessionMeta tracks first_message_time field."""
    now = datetime.now(UTC)
    
    meta = SessionMeta(
        session_id="sess_test123",
        created_at=now,
        last_active=now,
        status="active",
        first_message_time=now,
    )
    
    assert meta.first_message_time == now


def test_session_meta_first_message_time_defaults_to_none():
    """Verify first_message_time defaults to None."""
    now = datetime.now(UTC)
    
    meta = SessionMeta(
        session_id="sess_test123",
        created_at=now,
        last_active=now,
        status="active",
    )
    
    assert meta.first_message_time is None


def test_session_meta_tracks_last_summarized_count():
    """Verify SessionMeta tracks last_summarized_count field."""
    now = datetime.now(UTC)
    
    meta = SessionMeta(
        session_id="sess_test123",
        created_at=now,
        last_active=now,
        status="active",
        last_summarized_count=15,
    )
    
    assert meta.last_summarized_count == 15


def test_session_meta_last_summarized_count_defaults_to_zero():
    """Verify last_summarized_count defaults to 0."""
    now = datetime.now(UTC)
    
    meta = SessionMeta(
        session_id="sess_test123",
        created_at=now,
        last_active=now,
        status="active",
    )
    
    assert meta.last_summarized_count == 0


def test_session_meta_tracks_summary_version():
    """Verify SessionMeta tracks summary_version field."""
    now = datetime.now(UTC)
    
    meta = SessionMeta(
        session_id="sess_test123",
        created_at=now,
        last_active=now,
        status="active",
        summary_version=3,
    )
    
    assert meta.summary_version == 3


def test_session_meta_summary_version_defaults_to_zero():
    """Verify summary_version defaults to 0."""
    now = datetime.now(UTC)
    
    meta = SessionMeta(
        session_id="sess_test123",
        created_at=now,
        last_active=now,
        status="active",
    )
    
    assert meta.summary_version == 0
