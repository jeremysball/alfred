"""Tests for search_session_summaries function."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.search import search_session_summaries
from src.session import SessionSummary
from src.session_storage import SessionStorage


@pytest.mark.asyncio
async def test_search_session_summaries_finds_similar() -> None:
    """Verify embedding similarity search returns matching summaries."""
    # Arrange: Create mock summaries with different embeddings
    summary_one = SessionSummary(
        id="sum_one",
        session_id="sess_one",
        timestamp=datetime.now(UTC),
        message_range=(0, 10),
        message_count=10,
        summary_text="Discussion about Python async patterns",
        embedding=[0.9, 0.1, 0.1, 0.1],  # Similar to query
        version=1,
    )
    summary_two = SessionSummary(
        id="sum_two",
        session_id="sess_two",
        timestamp=datetime.now(UTC),
        message_range=(0, 5),
        message_count=5,
        summary_text="Discussion about database design",
        embedding=[0.1, 0.9, 0.1, 0.1],  # Less similar
        version=1,
    )

    storage = MagicMock(spec=SessionStorage)
    storage.list_sessions.return_value = ["sess_one", "sess_two"]
    storage.get_summary = AsyncMock(side_effect=[summary_one, summary_two])

    query_embedding = [0.95, 0.05, 0.05, 0.05]  # Should match summary_one closely

    # Act
    results = await search_session_summaries(
        query_embedding=query_embedding,
        storage=storage,
        top_k=5,
        min_similarity=0.0,  # Include all for test
    )

    # Assert
    assert len(results) == 2
    # First result should be the more similar one
    assert results[0]["session_id"] == "sess_one"
    assert results[0]["similarity"] > results[1]["similarity"]


@pytest.mark.asyncio
async def test_search_session_summaries_returns_top_k() -> None:
    """Verify top_k limit is respected."""
    # Arrange: Create more summaries than top_k
    summaries = [
        SessionSummary(
            id=f"sum_{i}",
            session_id=f"sess_{i}",
            timestamp=datetime.now(UTC),
            message_range=(0, i + 1),
            message_count=i + 1,
            summary_text=f"Summary {i}",
            embedding=[0.9 - i * 0.1, 0.1, 0.1, 0.1],
            version=1,
        )
        for i in range(10)
    ]

    storage = MagicMock(spec=SessionStorage)
    storage.list_sessions.return_value = [f"sess_{i}" for i in range(10)]
    storage.get_summary = AsyncMock(side_effect=summaries)

    query_embedding = [1.0, 0.0, 0.0, 0.0]

    # Act
    results = await search_session_summaries(
        query_embedding=query_embedding,
        storage=storage,
        top_k=3,
        min_similarity=0.0,
    )

    # Assert
    assert len(results) == 3


@pytest.mark.asyncio
async def test_search_session_summaries_skips_missing() -> None:
    """Verify sessions without summaries are skipped gracefully."""
    # Arrange
    summary = SessionSummary(
        id="sum_one",
        session_id="sess_one",
        timestamp=datetime.now(UTC),
        message_range=(0, 5),
        message_count=5,
        summary_text="Existing summary",
        embedding=[0.9, 0.1, 0.1, 0.1],
        version=1,
    )

    storage = MagicMock(spec=SessionStorage)
    storage.list_sessions.return_value = ["sess_one", "sess_two"]
    storage.get_summary = AsyncMock(side_effect=[summary, None])

    query_embedding = [1.0, 0.0, 0.0, 0.0]

    # Act
    results = await search_session_summaries(
        query_embedding=query_embedding,
        storage=storage,
        top_k=5,
        min_similarity=0.0,
    )

    # Assert
    assert len(results) == 1
    assert results[0]["session_id"] == "sess_one"


@pytest.mark.asyncio
async def test_search_session_summaries_respects_min_similarity() -> None:
    """Verify min_similarity filter excludes low-similarity results."""
    # Arrange
    summary_high = SessionSummary(
        id="sum_high",
        session_id="sess_high",
        timestamp=datetime.now(UTC),
        message_range=(0, 5),
        message_count=5,
        summary_text="High similarity",
        embedding=[0.95, 0.05, 0.0, 0.0],
        version=1,
    )
    summary_low = SessionSummary(
        id="sum_low",
        session_id="sess_low",
        timestamp=datetime.now(UTC),
        message_range=(0, 5),
        message_count=5,
        summary_text="Low similarity",
        embedding=[0.1, 0.9, 0.0, 0.0],
        version=1,
    )

    storage = MagicMock(spec=SessionStorage)
    storage.list_sessions.return_value = ["sess_high", "sess_low"]
    storage.get_summary = AsyncMock(side_effect=[summary_high, summary_low])

    query_embedding = [1.0, 0.0, 0.0, 0.0]

    # Act
    results = await search_session_summaries(
        query_embedding=query_embedding,
        storage=storage,
        top_k=5,
        min_similarity=0.7,  # Only high similarity should pass
    )

    # Assert
    assert len(results) == 1
    assert results[0]["session_id"] == "sess_high"
