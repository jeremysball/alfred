"""Tests for the forget tool."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from src.tools.forget import ForgetTool
from src.types import MemoryEntry


@pytest.fixture
def mock_memory_store():
    """Create a mock memory store."""
    store = Mock()
    store.search = AsyncMock()
    store.delete_entries = AsyncMock()
    return store


@pytest.fixture
def forget_tool(mock_memory_store):
    """Create a ForgetTool with mock store."""
    tool = ForgetTool()
    tool.set_memory_store(mock_memory_store)
    return tool


class TestForgetTool:
    """Test suite for ForgetTool."""

    def test_name_and_description(self):
        """Tool has correct name and description."""
        tool = ForgetTool()
        assert tool.name == "forget"
        assert "delete" in tool.description.lower() or "forget" in tool.description.lower()

    def test_execute_returns_error(self):
        """Sync execute returns error message."""
        tool = ForgetTool()
        result = tool.execute(query="test")
        assert "Error" in result
        assert "execute_stream" in result

    async def test_preview_no_matches(self, forget_tool, mock_memory_store):
        """Preview mode returns message when no matches found."""
        mock_memory_store.search.return_value = []

        result = ""
        async for chunk in forget_tool.execute_stream(query="nonexistent"):
            result += chunk

        assert "No memories found" in result
        mock_memory_store.search.assert_called_once_with("nonexistent", top_k=100)
        mock_memory_store.delete_entries.assert_not_called()

    async def test_preview_shows_matches(self, forget_tool, mock_memory_store):
        """Preview mode shows matching memories."""
        memories = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 14, 30),
                role="system",
                content="Old project idea about a chatbot",
                embedding=[0.1, 0.2],
                importance=0.5,
                tags=[],
            ),
            MemoryEntry(
                timestamp=datetime(2026, 2, 16, 10, 0),
                role="system",
                content="Another old project memory",
                embedding=[0.3, 0.4],
                importance=0.6,
                tags=[],
            ),
        ]
        mock_memory_store.search.return_value = memories

        result = ""
        async for chunk in forget_tool.execute_stream(query="old project"):
            result += chunk

        assert "Found 2 memories" in result
        assert "chatbot" in result
        assert "confirm=True" in result
        mock_memory_store.delete_entries.assert_not_called()

    async def test_preview_truncates_long_content(self, forget_tool, mock_memory_store):
        """Preview truncates long content to 60 chars."""
        memories = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17),
                role="system",
                content="A" * 100,  # Very long content
                embedding=[0.1, 0.2],
                importance=0.5,
                tags=[],
            ),
        ]
        mock_memory_store.search.return_value = memories

        result = ""
        async for chunk in forget_tool.execute_stream(query="test"):
            result += chunk

        # Should show "AAA..." not all 100 As
        assert "..." in result
        assert len(result) < 300  # Should be truncated (increased limit due to ID)

    async def test_preview_shows_more_indicator(self, forget_tool, mock_memory_store):
        """Preview shows 'and X more' when more than 5 matches."""
        memories = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17),
                role="system",
                content=f"Memory {i}",
                embedding=[0.1, 0.2],
                importance=0.5,
                tags=[],
            )
            for i in range(7)
        ]
        mock_memory_store.search.return_value = memories

        result = ""
        async for chunk in forget_tool.execute_stream(query="test"):
            result += chunk

        assert "and 2 more" in result

    async def test_confirmed_deletes(self, forget_tool, mock_memory_store):
        """Confirmed delete actually calls delete_entries."""
        mock_memory_store.delete_entries.return_value = (3, "Deleted 3 memories")

        result = ""
        async for chunk in forget_tool.execute_stream(
            query="old project",
            confirm=True,
        ):
            result += chunk

        assert "Deleted 3 memories" in result
        mock_memory_store.delete_entries.assert_called_once_with("old project")
        mock_memory_store.search.assert_not_called()

    async def test_confirmed_no_matches(self, forget_tool, mock_memory_store):
        """Confirmed delete handles no matches."""
        mock_memory_store.delete_entries.return_value = (
            0,
            "No memories matching query: xyz",
        )

        result = ""
        async for chunk in forget_tool.execute_stream(query="xyz", confirm=True):
            result += chunk

        assert "No memories matching" in result

    async def test_without_memory_store(self):
        """Error when memory store not initialized."""
        tool = ForgetTool()  # No store set

        result = ""
        async for chunk in tool.execute_stream(query="test"):
            result += chunk

        assert "Error" in result
        assert "not initialized" in result

    async def test_preview_error_handling(self, forget_tool, mock_memory_store):
        """Handles errors during preview gracefully."""
        mock_memory_store.search.side_effect = Exception("Search failed")

        result = ""
        async for chunk in forget_tool.execute_stream(query="test"):
            result += chunk

        assert "Error previewing memories" in result

    async def test_delete_error_handling(self, forget_tool, mock_memory_store):
        """Handles errors during delete gracefully."""
        mock_memory_store.delete_entries.side_effect = Exception("Delete failed")

        result = ""
        async for chunk in forget_tool.execute_stream(query="test", confirm=True):
            result += chunk

        assert "Error deleting memories" in result
