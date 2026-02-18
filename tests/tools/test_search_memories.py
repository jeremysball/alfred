"""Tests for the search_memories tool."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.tools.search_memories import SearchMemoriesTool
from src.types import MemoryEntry


@pytest.fixture
def mock_memory_store():
    """Create a mock memory store."""
    store = Mock()
    store.search = AsyncMock()
    return store


@pytest.fixture
def search_tool(mock_memory_store):
    """Create a SearchMemoriesTool with mock store."""
    tool = SearchMemoriesTool()
    tool.set_memory_store(mock_memory_store)
    return tool


class TestSearchMemoriesTool:
    """Test suite for SearchMemoriesTool."""

    def test_name_and_description(self):
        """Tool has correct name and description."""
        tool = SearchMemoriesTool()
        assert tool.name == "search_memories"
        assert "search" in tool.description.lower()

    def test_execute_returns_error(self):
        """Sync execute returns error message."""
        tool = SearchMemoriesTool()
        result = tool.execute(query="test")
        assert "Error" in result
        assert "execute_stream" in result

    async def test_search_returns_formatted_results(self, search_tool, mock_memory_store):
        """Search returns formatted memory results."""
        # Arrange
        memories = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 14, 30),
                role="system",
                content="User prefers Python over JavaScript",
                embedding=[0.1, 0.2],
                tags=[],
            ),
            MemoryEntry(
                timestamp=datetime(2026, 2, 16, 10, 0),
                role="system",
                content="User works remotely from Portland",
                embedding=[0.3, 0.4],
                tags=[],
            ),
        ]
        similarities = {memories[0].entry_id: 0.85, memories[1].entry_id: 0.65}
        mock_memory_store.search.return_value = (memories, similarities)

        # Act
        result = ""
        async for chunk in search_tool.execute_stream(query="Python", top_k=5):
            result += chunk

        # Assert
        assert "Python over JavaScript" in result
        assert "Portland" in result
        assert "85% match" in result or "65% match" in result
        assert "[2026-02-17]" in result
        mock_memory_store.search.assert_called_once_with("Python", top_k=5)

    async def test_search_no_results(self, search_tool, mock_memory_store):
        """Search with no results returns appropriate message."""
        mock_memory_store.search.return_value = ([], {})

        result = ""
        async for chunk in search_tool.execute_stream(query="unknown"):
            result += chunk

        assert "No relevant memories found" in result

    async def test_search_without_memory_store(self):
        """Error when memory store not initialized."""
        tool = SearchMemoriesTool()  # No store set

        result = ""
        async for chunk in tool.execute_stream(query="test"):
            result += chunk

        assert "Error" in result
        assert "not initialized" in result

    async def test_search_error_handling(self, search_tool, mock_memory_store):
        """Handles errors from memory store gracefully."""
        mock_memory_store.search.side_effect = Exception("Search failed")

        result = ""
        async for chunk in search_tool.execute_stream(query="test"):
            result += chunk

        assert "Error searching memories" in result
