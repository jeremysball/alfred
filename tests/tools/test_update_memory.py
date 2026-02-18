"""Tests for the update_memory tool."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.tools.update_memory import UpdateMemoryTool
from src.types import MemoryEntry


@pytest.fixture
def mock_memory_store():
    """Create a mock memory store."""
    store = Mock()
    store.update_entry = AsyncMock()
    store.search = AsyncMock()
    return store


@pytest.fixture
def update_tool(mock_memory_store):
    """Create an UpdateMemoryTool with mock store."""
    tool = UpdateMemoryTool()
    tool.set_memory_store(mock_memory_store)
    return tool


class TestUpdateMemoryTool:
    """Test suite for UpdateMemoryTool."""

    def test_name_and_description(self):
        """Tool has correct name and description."""
        tool = UpdateMemoryTool()
        assert tool.name == "update_memory"
        assert "update" in tool.description.lower()

    def test_execute_returns_error(self):
        """Sync execute returns error message."""
        tool = UpdateMemoryTool()
        result = tool.execute(search_query="test")
        assert "Error" in result
        assert "execute_stream" in result

    async def test_preview_content_only(self, update_tool, mock_memory_store):
        """Preview mode shows current memory and proposed content change."""
        memory = MemoryEntry(
            timestamp=datetime(2026, 2, 17, 14, 30),
            role="system",
            content="Old content here",
            embedding=[0.1, 0.2],
            tags=[],
        )
        mock_memory_store.search.return_value = ([memory], {})

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="old memory",
            new_content="New content here",
        ):
            result += chunk

        assert "Found memory to update" in result
        assert "Current:" in result
        assert "Old content here" in result
        assert "Will update to:" in result
        assert "New content: New content here" in result
        assert "confirm=True" in result
        mock_memory_store.search.assert_called_once_with("old memory", top_k=1)
        mock_memory_store.update_entry.assert_not_called()

    async def test_preview_importance_only(self, update_tool, mock_memory_store):
        """Importance field removed - test deprecated."""
        pytest.skip("Importance field removed from MemoryEntry")

    async def test_preview_both_fields(self, update_tool, mock_memory_store):
        """Preview mode shows content change."""
        memory = MemoryEntry(
            timestamp=datetime(2026, 2, 17),
            role="system",
            content="User name is John",
            embedding=[0.1, 0.2],
            tags=[],
        )
        mock_memory_store.search.return_value = ([memory], {})

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="user name",
            new_content="User name is Jasmine",
        ):
            result += chunk

        assert "Found memory to update" in result
        assert "New content: User name is Jasmine" in result

    async def test_preview_no_matches(self, update_tool, mock_memory_store):
        """Preview mode returns message when no matches found."""
        mock_memory_store.search.return_value = ([], {})

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="nonexistent",
            new_content="update",
        ):
            result += chunk

        assert "No memory found" in result
        mock_memory_store.update_entry.assert_not_called()

    async def test_confirmed_update(self, update_tool, mock_memory_store):
        """Confirmed update calls update_entry."""
        mock_memory_store.update_entry.return_value = (
            True,
            "Updated: New content here",
        )

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="old memory",
            new_content="New content here",
            confirm=True,
        ):
            result += chunk

        assert "Updated" in result
        mock_memory_store.update_entry.assert_called_once_with(
            search_query="old memory",
            new_content="New content here",
        )
        mock_memory_store.search.assert_not_called()

    async def test_confirmed_update_not_found(self, update_tool, mock_memory_store):
        """Confirmed update handles not found case."""
        mock_memory_store.update_entry.return_value = (
            False,
            "No matching memory found for query: xyz",
        )

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="xyz",
            new_content="update",
            confirm=True,
        ):
            result += chunk

        assert "No matching memory" in result

    async def test_no_changes_specified(self, update_tool):
        """Error when no changes specified."""
        result = ""
        async for chunk in update_tool.execute_stream(search_query="test"):
            result += chunk

        assert "Error" in result
        assert "Specify new_content" in result
        mock_memory_store = update_tool._memory_store
        mock_memory_store.search.assert_not_called()
        mock_memory_store.update_entry.assert_not_called()

    async def test_without_memory_store(self):
        """Error when memory store not initialized."""
        tool = UpdateMemoryTool()  # No store set

        result = ""
        async for chunk in tool.execute_stream(
            search_query="test",
            new_content="update",
        ):
            result += chunk

        assert "Error" in result
        assert "not initialized" in result

    async def test_preview_error_handling(self, update_tool, mock_memory_store):
        """Handles errors during preview gracefully."""
        mock_memory_store.search.side_effect = Exception("Search failed")

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="test",
            new_content="update",
        ):
            result += chunk

        assert "Error previewing update" in result

    async def test_update_error_handling(self, update_tool, mock_memory_store):
        """Handles errors during update gracefully."""
        mock_memory_store.update_entry.side_effect = Exception("Update failed")

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="test",
            new_content="update",
            confirm=True,
        ):
            result += chunk

        assert "Error updating memory" in result
