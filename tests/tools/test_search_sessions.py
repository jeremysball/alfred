"""Tests for the search_sessions tool (JSON output)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.session import SessionSummary
from src.session_storage import SessionStorage
from src.tools.search_sessions import SearchSessionsTool


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Create a mock embedder."""
    embedder = MagicMock()
    embedder.embed = AsyncMock(return_value=[1.0, 0.0, 0.0, 0.0])
    return embedder


@pytest.fixture
def session_storage(tmp_path: Path, mock_embedder: MagicMock) -> SessionStorage:
    """Create SessionStorage with a temporary data directory."""
    return SessionStorage(embedder=mock_embedder, data_dir=tmp_path)


def _collect_json(chunks: list[str]) -> dict:
    return json.loads("".join(chunks))


class TestSearchSessionsTool:
    """Tests for SearchSessionsTool."""

    def test_search_sessions_tool_exists(self) -> None:
        """Tool has correct name and description."""
        tool = SearchSessionsTool(storage=MagicMock(), embedder=MagicMock())
        assert tool.name == "search_sessions"
        assert tool.description

    async def test_search_sessions_tool_requires_dependencies(self) -> None:
        """Missing storage/embedder returns error JSON."""
        tool = SearchSessionsTool(storage=None, embedder=None)

        chunks: list[str] = []
        async for chunk in tool.execute_stream(query="sessions", top_k=2):
            chunks.append(chunk)

        result = _collect_json(chunks)
        assert result["success"] is False
        assert "not initialized" in result["error"].lower()
        assert result["count"] == 0
        assert result["results"] == []

    async def test_search_sessions_tool_requires_query(
        self, session_storage: SessionStorage, mock_embedder: MagicMock
    ) -> None:
        """Empty query returns error JSON."""
        tool = SearchSessionsTool(storage=session_storage, embedder=mock_embedder)

        chunks: list[str] = []
        async for chunk in tool.execute_stream(query=""):
            chunks.append(chunk)

        result = _collect_json(chunks)
        assert result["success"] is False
        assert "query" in result["error"].lower()

    async def test_search_sessions_tool_returns_results(
        self, session_storage: SessionStorage, mock_embedder: MagicMock
    ) -> None:
        """Returns JSON results with summary_text."""
        summary = SessionSummary(
            id="sum_123",
            session_id="sess_123",
            timestamp=datetime(2026, 3, 1, tzinfo=UTC),
            message_range=(0, 2),
            message_count=2,
            summary_text="Discussed session summarization.",
            embedding=[1.0, 0.0, 0.0, 0.0],
            version=1,
        )
        await session_storage.store_summary(summary)

        tool = SearchSessionsTool(storage=session_storage, embedder=mock_embedder)

        chunks: list[str] = []
        async for chunk in tool.execute_stream(query="session summarization", top_k=3):
            chunks.append(chunk)

        result = _collect_json(chunks)
        assert result["success"] is True
        assert result["count"] == 1
        assert result["results"][0]["session_id"] == "sess_123"
        assert result["results"][0]["summary_text"] == "Discussed session summarization."

    async def test_search_sessions_tool_returns_empty_results(
        self, session_storage: SessionStorage, mock_embedder: MagicMock
    ) -> None:
        """No matches yields empty results."""
        tool = SearchSessionsTool(storage=session_storage, embedder=mock_embedder)

        chunks: list[str] = []
        async for chunk in tool.execute_stream(query="no matches", top_k=3):
            chunks.append(chunk)

        result = _collect_json(chunks)
        assert result["success"] is True
        assert result["count"] == 0
        assert result["results"] == []

    async def test_search_sessions_tool_uses_default_top_k(
        self, session_storage: SessionStorage, mock_embedder: MagicMock
    ) -> None:
        """Default top_k is 3."""
        for idx in range(5):
            summary = SessionSummary(
                id=f"sum_{idx}",
                session_id=f"sess_{idx}",
                timestamp=datetime(2026, 3, 1, tzinfo=UTC),
                message_range=(0, 1),
                message_count=1,
                summary_text=f"Summary {idx}",
                embedding=[1.0, 0.0, 0.0, 0.0],
                version=1,
            )
            await session_storage.store_summary(summary)

        tool = SearchSessionsTool(storage=session_storage, embedder=mock_embedder)

        chunks: list[str] = []
        async for chunk in tool.execute_stream(query="summary"):
            chunks.append(chunk)

        result = _collect_json(chunks)
        assert result["top_k"] == 3
        assert result["count"] == 3
        assert len(result["results"]) == 3
