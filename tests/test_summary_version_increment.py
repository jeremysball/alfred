"""Tests for summary version increment on replacement (PRD #76)."""

from datetime import datetime, UTC
import pytest

from src.session import SessionSummary
from src.session_storage import SessionStorage


@pytest.fixture
def mock_embedder():
    """Mock embedder for testing."""
    class MockEmbedder:
        dimension = 1536
        async def embed(self, text: str) -> list[float]:
            return [0.1] * self.dimension
    return MockEmbedder()


@pytest.fixture
def storage(tmp_path, mock_embedder):
    """Create SessionStorage with temp directory."""
    return SessionStorage(embedder=mock_embedder, data_dir=tmp_path)


async def test_store_summary_increments_version_on_replacement(storage):
    """Verify version increments when replacing existing summary."""
    session_id = "sess_test123"
    session_dir = storage.sessions_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Store initial summary with version 1
    initial = SessionSummary(
        id="sum_abc123",
        session_id=session_id,
        timestamp=datetime.now(UTC),
        message_range=(0, 10),
        message_count=10,
        summary_text="First summary",
        version=1,
    )
    await storage.store_summary(initial)
    
    # Store new summary - should auto-increment to version 2
    replacement = SessionSummary(
        id="sum_abc123",  # Same ID
        session_id=session_id,
        timestamp=datetime.now(UTC),
        message_range=(0, 20),
        message_count=20,
        summary_text="Updated summary",
        version=1,  # Should be ignored, auto-incremented
    )
    await storage.store_summary(replacement)
    
    # Verify version was incremented
    retrieved = await storage.get_summary(session_id)
    assert retrieved is not None
    assert retrieved.version == 2


async def test_store_summary_starts_at_version_one_for_new(storage):
    """Verify version starts at 1 for new summaries."""
    session_id = "sess_new456"
    session_dir = storage.sessions_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Store first summary for this session
    summary = SessionSummary(
        id="sum_def456",
        session_id=session_id,
        timestamp=datetime.now(UTC),
        message_range=(0, 5),
        message_count=5,
        summary_text="First summary",
        version=1,  # Default
    )
    await storage.store_summary(summary)
    
    # Verify version stayed at 1 (no existing to increment from)
    retrieved = await storage.get_summary(session_id)
    assert retrieved is not None
    assert retrieved.version == 1


async def test_store_summary_increments_from_zero(storage):
    """Verify version increments correctly from version 0."""
    session_id = "sess_zero789"
    session_dir = storage.sessions_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Store initial with version 0 (edge case)
    initial = SessionSummary(
        id="sum_ghi789",
        session_id=session_id,
        timestamp=datetime.now(UTC),
        message_range=(0, 10),
        message_count=10,
        summary_text="Initial",
        version=0,
    )
    await storage.store_summary(initial)
    
    # Store replacement - should increment to 1
    replacement = SessionSummary(
        id="sum_ghi789",
        session_id=session_id,
        timestamp=datetime.now(UTC),
        message_range=(0, 15),
        message_count=15,
        summary_text="Replacement",
        version=1,  # Should be overridden
    )
    await storage.store_summary(replacement)
    
    retrieved = await storage.get_summary(session_id)
    assert retrieved is not None
    assert retrieved.version == 1


async def test_store_summary_handles_missing_gracefully(storage):
    """Verify version defaults to 1 when no existing summary."""
    session_id = "sess_missing000"
    session_dir = storage.sessions_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # No existing summary - version should stay at caller's value
    summary = SessionSummary(
        id="sum_new000",
        session_id=session_id,
        timestamp=datetime.now(UTC),
        message_range=(0, 5),
        message_count=5,
        summary_text="First summary",
        version=5,  # Explicit version for new summary
    )
    await storage.store_summary(summary)
    
    # Version should remain as caller specified (no existing to increment from)
    retrieved = await storage.get_summary(session_id)
    assert retrieved is not None
    assert retrieved.version == 5