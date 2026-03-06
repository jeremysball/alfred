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


def test_session_summary_to_dict_serializes_all_fields():
    """Verify to_dict() serializes all fields correctly."""
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
    
    data = summary.to_dict()
    
    assert data["id"] == "sum_abc123def456"
    assert data["session_id"] == "sess_xyz789abc012"
    assert data["timestamp"] == now.isoformat()
    assert data["message_range"] == [0, 25]  # Tuple becomes list in JSON
    assert data["message_count"] == 25
    assert data["summary_text"] == "User and Alfred discussed database architecture..."
    assert data["embedding"] == [0.023, -0.156, 0.089]
    assert data["version"] == 1


def test_session_summary_to_dict_handles_none_embedding():
    """Verify to_dict() handles None embedding."""
    now = datetime.now(UTC)
    
    summary = SessionSummary(
        id="sum_abc123def456",
        session_id="sess_xyz789abc012",
        timestamp=now,
        message_range=(0, 10),
        message_count=10,
        summary_text="Test summary",
        embedding=None,
    )
    
    data = summary.to_dict()
    
    assert data["embedding"] is None


def test_session_summary_from_dict_deserializes_all_fields():
    """Verify from_dict() deserializes all fields correctly."""
    now = datetime.now(UTC)
    data = {
        "id": "sum_abc123def456",
        "session_id": "sess_xyz789abc012",
        "timestamp": now.isoformat(),
        "message_range": [0, 25],
        "message_count": 25,
        "summary_text": "User and Alfred discussed database architecture...",
        "embedding": [0.023, -0.156, 0.089],
        "version": 1,
    }
    
    summary = SessionSummary.from_dict(data)
    
    assert summary.id == "sum_abc123def456"
    assert summary.session_id == "sess_xyz789abc012"
    assert summary.timestamp == now
    assert summary.message_range == (0, 25)  # List becomes tuple
    assert summary.message_count == 25
    assert summary.summary_text == "User and Alfred discussed database architecture..."
    assert summary.embedding == [0.023, -0.156, 0.089]
    assert summary.version == 1


def test_session_summary_from_dict_handles_none_embedding():
    """Verify from_dict() handles None embedding."""
    now = datetime.now(UTC)
    data = {
        "id": "sum_abc123def456",
        "session_id": "sess_xyz789abc012",
        "timestamp": now.isoformat(),
        "message_range": [0, 10],
        "message_count": 10,
        "summary_text": "Test summary",
        "embedding": None,
        "version": 1,
    }
    
    summary = SessionSummary.from_dict(data)
    
    assert summary.embedding is None


def test_session_summary_roundtrip_preserves_data():
    """Verify to_dict() -> from_dict() roundtrip preserves all data."""
    now = datetime.now(UTC)
    original = SessionSummary(
        id="sum_abc123def456",
        session_id="sess_xyz789abc012",
        timestamp=now,
        message_range=(0, 25),
        message_count=25,
        summary_text="User and Alfred discussed database architecture...",
        embedding=[0.023, -0.156, 0.089],
        version=1,
    )
    
    data = original.to_dict()
    restored = SessionSummary.from_dict(data)
    
    assert restored.id == original.id
    assert restored.session_id == original.session_id
    assert restored.timestamp == original.timestamp
    assert restored.message_range == original.message_range
    assert restored.message_count == original.message_count
    assert restored.summary_text == original.summary_text
    assert restored.embedding == original.embedding
    assert restored.version == original.version
