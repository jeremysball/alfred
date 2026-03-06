"""Tests for SessionSummary dataclass (PRD #76)."""

from datetime import datetime, UTC
from src.session import SessionSummary


def test_session_summary_has_required_fields():
    """Verify SessionSummary dataclass has all required fields."""
    now = datetime.now(UTC)
    
    summary = SessionSummary(
        id="sum_abc123def456",
        session_id="sess_xyz789abc012",
        timestamp=now,
        message_range=(0, 25),
        message_count=25,
        summary_text="User and Alfred discussed database architecture...",
        embedding=[0.023, -0.156, 0.089],
        version=1,
    )
    
    assert summary.id == "sum_abc123def456"
    assert summary.session_id == "sess_xyz789abc012"
    assert summary.timestamp == now
    assert summary.message_range == (0, 25)
    assert summary.message_count == 25
    assert summary.summary_text == "User and Alfred discussed database architecture..."
    assert summary.embedding == [0.023, -0.156, 0.089]
    assert summary.version == 1


def test_session_summary_embedding_defaults_to_none():
    """Verify embedding defaults to None."""
    now = datetime.now(UTC)
    
    summary = SessionSummary(
        id="sum_abc123def456",
        session_id="sess_xyz789abc012",
        timestamp=now,
        message_range=(0, 10),
        message_count=10,
        summary_text="Test summary",
    )
    
    assert summary.embedding is None


def test_session_summary_version_defaults_to_one():
    """Verify version defaults to 1."""
    now = datetime.now(UTC)
    
    summary = SessionSummary(
        id="sum_abc123def456",
        session_id="sess_xyz789abc012",
        timestamp=now,
        message_range=(0, 10),
        message_count=10,
        summary_text="Test summary",
    )
    
    assert summary.version == 1
