"""Tests for the update_memory tool."""

import pytest
from unittest.mock import AsyncMock, Mock

from src.tools.update_memory import UpdateMemoryTool


@pytest.fixture
def mock_memory_store():
    """Create a mock memory store."""
    store = Mock()
    store.update_entry = AsyncMock()
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

    async def test_update_content_only(self, update_tool, mock_memory_store):
        """Update only content."""
        mock_memory_store.update_entry.return_value = (
            True,
            "Updated: New content here",
        )

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="old memory",
            new_content="New content here",
        ):
            result += chunk

        assert "Updated" in result
        mock_memory_store.update_entry.assert_called_once_with(
            search_query="old memory",
            new_content="New content here",
            new_importance=None,
        )

    async def test_update_importance_only(self, update_tool, mock_memory_store):
        """Update only importance."""
        mock_memory_store.update_entry.return_value = (
            True,
            "Updated: Memory content",
        )

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="memory",
            new_importance=0.9,
        ):
            result += chunk

        assert "Updated" in result
        mock_memory_store.update_entry.assert_called_once_with(
            search_query="memory",
            new_content=None,
            new_importance=0.9,
        )

    async def test_update_both_fields(self, update_tool, mock_memory_store):
        """Update both content and importance."""
        mock_memory_store.update_entry.return_value = (
            True,
            "Updated: New content",
        )

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="user name",
            new_content="User is Jasmine",
            new_importance=0.95,
        ):
            result += chunk

        assert "Updated" in result
        mock_memory_store.update_entry.assert_called_once_with(
            search_query="user name",
            new_content="User is Jasmine",
            new_importance=0.95,
        )

    async def test_update_no_changes_specified(self, update_tool):
        """Error when no changes specified."""
        result = ""
        async for chunk in update_tool.execute_stream(search_query="test"):
            result += chunk

        assert "Error" in result
        assert "Specify at least one" in result
        mock_memory_store = update_tool._memory_store
        mock_memory_store.update_entry.assert_not_called()

    async def test_update_not_found(self, update_tool, mock_memory_store):
        """Handle memory not found."""
        mock_memory_store.update_entry.return_value = (
            False,
            "No matching memory found for query: old project",
        )

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="old project",
            new_content="new info",
        ):
            result += chunk

        assert "No matching memory" in result

    async def test_update_without_memory_store(self):
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

    async def test_update_error_handling(self, update_tool, mock_memory_store):
        """Handles errors from memory store gracefully."""
        mock_memory_store.update_entry.side_effect = Exception("Update failed")

        result = ""
        async for chunk in update_tool.execute_stream(
            search_query="test",
            new_content="update",
        ):
            result += chunk

        assert "Error updating memory" in result
