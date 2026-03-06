"""Tests for summary storage operations (PRD #76)."""

import json
from datetime import datetime, UTC
from pathlib import Path
import pytest

from src.session import SessionSummary
from src.session_storage import SessionStorage
from src.embeddings.openai_provider import OpenAIProvider


@pytest.fixture
def mock_embedder():
    """Mock embedder for testing."""
    # Create a minimal mock
    class MockEmbedder:
        dimension = 1536
        async def embed(self, text: str) -> list[float]:
            return [0.1] * self.dimension
    return MockEmbedder()


@pytest.fixture
def storage(tmp_path, mock_embedder):
    """Create SessionStorage with temp directory."""
    return SessionStorage(embedder=mock_embedder, data_dir=tmp_path)


@pytest.fixture
def sample_summary():
    """Create a sample SessionSummary for testing."""
    return SessionSummary(
        id="sum_abc123def456",
        session_id="sess_xyz789abc012",
        timestamp=datetime(2026, 3, 6, 14, 30, 0, tzinfo=UTC),
        message_range=(0, 25),
        message_count=25,
        summary_text="User and Alfred discussed database architecture...",
        embedding=[0.023, -0.156, 0.089],
        version=1,
    )


async def test_store_summary_writes_to_json_file(storage, sample_summary):
    """Verify store_summary writes summary to summary.json."""
    # Create session folder first
    session_dir = storage.sessions_dir / sample_summary.session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Store the summary
    await storage.store_summary(sample_summary)
    
    # Verify file exists
    summary_path = session_dir / "summary.json"
    assert summary_path.exists()
    
    # Verify content
    data = json.loads(summary_path.read_text())
    assert data["id"] == sample_summary.id
    assert data["session_id"] == sample_summary.session_id
    assert data["message_count"] == 25
    assert data["summary_text"] == "User and Alfred discussed database architecture..."
    assert data["version"] == 1


async def test_get_summary_returns_existing_summary(storage, sample_summary):
    """Verify get_summary returns SessionSummary when file exists."""
    # Create session folder and store summary
    session_dir = storage.sessions_dir / sample_summary.session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    await storage.store_summary(sample_summary)
    
    # Retrieve the summary
    retrieved = await storage.get_summary(sample_summary.session_id)
    
    # Verify it's a SessionSummary with correct data
    assert retrieved is not None
    assert isinstance(retrieved, SessionSummary)
    assert retrieved.id == sample_summary.id
    assert retrieved.session_id == sample_summary.session_id
    assert retrieved.message_count == sample_summary.message_count
    assert retrieved.summary_text == sample_summary.summary_text
    assert retrieved.embedding == sample_summary.embedding
    assert retrieved.version == sample_summary.version


async def test_get_summary_returns_none_when_missing(storage):
    """Verify get_summary returns None when summary.json doesn't exist."""
    # Try to get summary for non-existent session
    retrieved = await storage.get_summary("sess_nonexistent123")
    
    # Should return None, not raise
    assert retrieved is None


async def test_store_summary_overwrites_existing(storage, sample_summary):
    """Verify store_summary overwrites existing summary (caller handles versioning)."""
    # Create session folder
    session_dir = storage.sessions_dir / sample_summary.session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Store initial summary
    await storage.store_summary(sample_summary)
    
    # Create updated summary with same ID but different content
    updated_summary = SessionSummary(
        id=sample_summary.id,  # Same ID
        session_id=sample_summary.session_id,
        timestamp=datetime(2026, 3, 6, 15, 0, 0, tzinfo=UTC),
        message_range=(0, 30),
        message_count=30,
        summary_text="Updated summary with more context...",
        embedding=[0.5, -0.2, 0.1],
        version=2,  # Version incremented by caller
    )
    
    # Store updated summary (should overwrite)
    await storage.store_summary(updated_summary)
    
    # Verify updated content
    retrieved = await storage.get_summary(sample_summary.session_id)
    assert retrieved is not None
    assert retrieved.message_count == 30
    assert retrieved.summary_text == "Updated summary with more context..."
    assert retrieved.version == 2
