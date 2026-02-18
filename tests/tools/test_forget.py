"""Tests for the forget tool with ID-based deletion and call-tracking confirmation."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.tools.forget import ForgetTool, PendingDeletion
from src.types import MemoryEntry


@pytest.fixture
def mock_memory_store():
    """Create a mock memory store."""
    store = Mock()
    store.search = AsyncMock()
    store.get_by_id = AsyncMock()
    store.delete_by_id = AsyncMock()
    return store


@pytest.fixture
def forget_tool(mock_memory_store):
    """Create a ForgetTool with mock store."""
    tool = ForgetTool()
    tool.set_memory_store(mock_memory_store)
    return tool


@pytest.fixture
def sample_memory():
    """Create a sample memory entry."""
    return MemoryEntry(
        timestamp=datetime(2026, 2, 17, 14, 30),
        role="system",
        content="User lives in San Francisco",
        embedding=[0.1, 0.2],
        tags=[],
    )


class TestForgetTool:
    """Test suite for ForgetTool."""

    def test_name_and_description(self):
        """Tool has correct name and description."""
        tool = ForgetTool()
        assert tool.name == "forget"
        assert "delete" in tool.description.lower()
        assert "two" in tool.description.lower() or "confirm" in tool.description.lower()

    def test_execute_returns_error(self):
        """Sync execute returns error message."""
        tool = ForgetTool()
        result = tool.execute(memory_id="test")
        assert "Error" in result
        assert "execute_stream" in result

    async def test_query_no_matches(self, forget_tool, mock_memory_store):
        """Query mode returns message when no matches found."""
        mock_memory_store.search.return_value = ([], [], {})

        result = ""
        async for chunk in forget_tool.execute_stream(query="nonexistent"):
            result += chunk

        assert "No memories found" in result
        mock_memory_store.search.assert_called_once_with("nonexistent", top_k=10)
        mock_memory_store.delete_by_id.assert_not_called()

    async def test_query_shows_matches(self, forget_tool, mock_memory_store):
        """Query mode shows matching memories with IDs."""
        memories = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 14, 30),
                role="system",
                content="Old project idea about a chatbot",
                embedding=[0.1, 0.2],
                tags=[],
            ),
            MemoryEntry(
                timestamp=datetime(2026, 2, 16, 10, 0),
                role="system",
                content="Another old project memory",
                embedding=[0.3, 0.4],
                tags=[],
            ),
        ]
        memories[0].entry_id = "abc123"
        memories[1].entry_id = "def456"
        mock_memory_store.search.return_value = (memories, {"abc123": 0.9, "def456": 0.8}, {})

        result = ""
        async for chunk in forget_tool.execute_stream(query="old project"):
            result += chunk

        assert "Found 2 memories" in result
        assert "abc123" in result
        assert "def456" in result
        assert "90%" in result or "80%" in result
        mock_memory_store.delete_by_id.assert_not_called()

    async def test_query_truncates_long_content(self, forget_tool, mock_memory_store):
        """Query mode truncates long content."""
        memories = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17),
                role="system",
                content="A" * 100,  # Very long content
                embedding=[0.1, 0.2],
                tags=[],
            ),
        ]
        memories[0].entry_id = "long123"
        mock_memory_store.search.return_value = (memories, {"long123": 0.95}, {})

        result = ""
        async for chunk in forget_tool.execute_stream(query="test"):
            result += chunk

        # Should show truncated content with ID
        assert "long123" in result
        assert "..." in result or len(result) < 300

    async def test_memory_id_first_call_creates_pending(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """First call with memory_id creates pending deletion."""
        sample_memory.entry_id = "mem123"
        mock_memory_store.get_by_id.return_value = sample_memory

        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="mem123"):
            result += chunk

        assert "Please confirm" in result
        assert "mem123" in result
        mock_memory_store.delete_by_id.assert_not_called()
        assert "mem123" in forget_tool._pending_deletions

    async def test_memory_id_second_call_executes(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """Second call with same memory_id executes deletion."""
        sample_memory.entry_id = "mem123"
        mock_memory_store.get_by_id.return_value = sample_memory
        mock_memory_store.delete_by_id.return_value = (True, "Memory deleted")

        # First call
        async for _ in forget_tool.execute_stream(memory_id="mem123"):
            pass

        # Second call
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="mem123"):
            result += chunk

        assert "deleted" in result.lower()
        mock_memory_store.delete_by_id.assert_called_once_with("mem123")
        assert "mem123" not in forget_tool._pending_deletions

    async def test_different_id_starts_new_pending(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """Different memory_id on second call starts new pending."""
        sample_memory.entry_id = "abc123"
        other = MemoryEntry(
            timestamp=datetime(2026, 2, 16),
            role="system",
            content="Different memory",
            embedding=[0.3, 0.4],
            tags=[],
        )
        other.entry_id = "xyz789"

        mock_memory_store.get_by_id.side_effect = [sample_memory, other]

        # First call with abc123
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        assert "abc123" in forget_tool._pending_deletions

        # Second call with xyz789
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="xyz789"):
            result += chunk

        assert "Please confirm" in result
        assert "xyz789" in forget_tool._pending_deletions
        mock_memory_store.delete_by_id.assert_not_called()

    async def test_without_memory_store(self):
        """Error when memory store not initialized."""
        tool = ForgetTool()  # No store set

        result = ""
        async for chunk in tool.execute_stream(memory_id="test"):
            result += chunk

        assert "Error" in result
        assert "not initialized" in result

    async def test_invalid_memory_id(self, forget_tool, mock_memory_store):
        """Error for invalid memory_id."""
        mock_memory_store.get_by_id.return_value = None

        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="invalid"):
            result += chunk

        assert "Error" in result or "not found" in result.lower()

    async def test_missing_parameters(self, forget_tool):
        """Error when neither memory_id nor query provided."""
        result = ""
        async for chunk in forget_tool.execute_stream():
            result += chunk

        assert "Error" in result

    async def test_query_error_handling(self, forget_tool, mock_memory_store):
        """Handles errors during query gracefully."""
        mock_memory_store.search.side_effect = Exception("Search failed")

        result = ""
        async for chunk in forget_tool.execute_stream(query="test"):
            result += chunk

        assert "Error" in result

    async def test_get_by_id_error_handling(self, forget_tool, mock_memory_store):
        """Handles errors during get_by_id gracefully."""
        mock_memory_store.get_by_id.side_effect = Exception("DB error")

        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="test"):
            result += chunk

        assert "Error" in result

    async def test_delete_error_handling(self, forget_tool, mock_memory_store, sample_memory):
        """Handles errors during delete gracefully."""
        sample_memory.entry_id = "mem123"
        mock_memory_store.get_by_id.return_value = sample_memory
        mock_memory_store.delete_by_id.side_effect = Exception("Delete failed")

        # First call
        async for _ in forget_tool.execute_stream(memory_id="mem123"):
            pass

        # Second call
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="mem123"):
            result += chunk

        assert "Error" in result


class TestPendingDeletion:
    """Test suite for PendingDeletion dataclass."""

    def test_creation(self):
        """Can create PendingDeletion."""
        pending = PendingDeletion(
            memory_id="abc123",
            content_preview="Test content",
        )
        assert pending.memory_id == "abc123"
        assert pending.content_preview == "Test content"
        assert pending.request_count == 1

    def test_is_expired_true(self):
        """Returns True when expired."""
        old_time = datetime.now() - __import__("datetime").timedelta(minutes=10)
        pending = PendingDeletion(
            memory_id="abc123",
            content_preview="Test",
            requested_at=old_time,
        )
        assert pending.is_expired() is True

    def test_is_expired_false(self):
        """Returns False when not expired."""
        recent = datetime.now() - __import__("datetime").timedelta(minutes=1)
        pending = PendingDeletion(
            memory_id="abc123",
            content_preview="Test",
            requested_at=recent,
        )
        assert pending.is_expired() is False
