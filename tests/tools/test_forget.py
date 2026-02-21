"""Tests for the forget tool with ID-based deletion and two-call confirmation."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from src.tools.forget import ForgetTool, PendingDeletion
from src.types import MemoryEntry


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_memory_store():
    """Create a mock memory store with async methods."""
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


# ============================================================================
# PendingDeletion Dataclass Tests
# ============================================================================


class TestPendingDeletion:
    """Test suite for PendingDeletion dataclass."""

    def test_creation(self):
        """Can create PendingDeletion with all fields."""
        now = datetime.now()
        pending = PendingDeletion(
            memory_id="abc123",
            content_preview="User lives in SF",
            requested_at=now,
            request_count=1,
        )
        assert pending.memory_id == "abc123"
        assert pending.content_preview == "User lives in SF"
        assert pending.requested_at == now
        assert pending.request_count == 1

    def test_defaults(self):
        """PendingDeletion uses sensible defaults."""
        pending = PendingDeletion(
            memory_id="abc123",
            content_preview="Test",
            requested_at=datetime.now(),
        )
        assert pending.request_count == 1

    def test_is_expired_true(self):
        """Returns True when expired (after 5 minutes)."""
        old_time = datetime.now() - timedelta(minutes=6)
        pending = PendingDeletion(
            memory_id="abc123",
            content_preview="Test",
            requested_at=old_time,
        )
        assert pending.is_expired() is True

    def test_is_expired_false(self):
        """Returns False when not expired."""
        recent = datetime.now() - timedelta(minutes=1)
        pending = PendingDeletion(
            memory_id="abc123",
            content_preview="Test",
            requested_at=recent,
        )
        assert pending.is_expired() is False


# ============================================================================
# Tool Interface Tests
# ============================================================================


class TestToolInterface:
    """Test suite for tool interface and metadata."""

    def test_tool_name(self):
        """Tool has correct name."""
        tool = ForgetTool()
        assert tool.name == "forget"

    def test_tool_description(self):
        """Tool description explains the two-call pattern."""
        tool = ForgetTool()
        desc = tool.description.lower()
        assert "two" in desc or "confirm" in desc or "twice" in desc
        assert "delete" in desc

    def test_has_memory_id_parameter(self):
        """Tool has memory_id parameter."""
        tool = ForgetTool()
        params = tool.param_model.model_fields
        assert "memory_id" in params

    def test_has_query_parameter(self):
        """Tool has query parameter."""
        tool = ForgetTool()
        params = tool.param_model.model_fields
        assert "query" in params

    def test_sync_execute_returns_error(self):
        """Sync execute returns error directing to async method."""
        tool = ForgetTool()
        result = tool.execute(memory_id="test")
        assert "Error" in result
        assert "execute_stream" in result


# ============================================================================
# Two-Call Confirmation Pattern Tests
# ============================================================================


class TestTwoCallConfirmation:
    """Test suite for two-call confirmation pattern."""

    @pytest.mark.asyncio
    async def test_first_call_creates_pending(self, forget_tool, mock_memory_store, sample_memory):
        """First call with memory_id creates pending deletion."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory

        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="abc123"):
            result += chunk

        assert "Please confirm" in result
        assert "abc123" in result
        assert "San Francisco" in result
        assert "abc123" in forget_tool._pending_deletions
        mock_memory_store.delete_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_second_call_executes_deletion(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """Second call with same memory_id executes deletion."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory
        mock_memory_store.delete_by_id.return_value = (True, "Deleted successfully")

        # First call
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass

        # Second call
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="abc123"):
            result += chunk

        assert "Deleted successfully" in result
        mock_memory_store.delete_by_id.assert_called_once_with("abc123")
        assert "abc123" not in forget_tool._pending_deletions

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_request_count_increments(self, forget_tool, mock_memory_store, sample_memory):
        """Request count increments on each call."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory
        mock_memory_store.delete_by_id.return_value = (True, "Deleted")

        # First call - count = 1
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        assert forget_tool._pending_deletions["abc123"].request_count == 1

        # Second call - executes deletion, clears pending
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        assert "abc123" not in forget_tool._pending_deletions

        # Third call - starts fresh
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        assert forget_tool._pending_deletions["abc123"].request_count == 1


# ============================================================================
# Expiration Tests
# ============================================================================


class TestExpiration:
    """Test suite for pending deletion expiration."""

    @pytest.mark.asyncio
    async def test_pending_expires_after_5_minutes(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """Pending deletion expires after 5 minutes."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory

        # First call
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass

        # Manually expire
        old_time = datetime.now() - timedelta(minutes=6)
        forget_tool._pending_deletions["abc123"].requested_at = old_time

        # Second call should require new confirmation
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="abc123"):
            result += chunk

        assert "Please confirm" in result
        mock_memory_store.delete_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_fresh_pending_executes_deletion(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """Non-expired pending executes deletion on second call."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory
        mock_memory_store.delete_by_id.return_value = (True, "Deleted")

        # First call
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass

        # Set time to just 1 minute ago (not expired)
        recent_time = datetime.now() - timedelta(minutes=1)
        forget_tool._pending_deletions["abc123"].requested_at = recent_time

        # Second call should execute
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="abc123"):
            result += chunk

        assert "Deleted" in result
        mock_memory_store.delete_by_id.assert_called_once()


# ============================================================================
# Query Mode Tests
# ============================================================================


class TestQueryMode:
    """Test suite for query-based candidate discovery."""

    @pytest.mark.asyncio
    async def test_query_returns_candidates(self, forget_tool, mock_memory_store):
        """Query mode returns list of candidates with IDs."""
        memories = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 14, 30),
                role="system",
                content="User lives in San Francisco",
                embedding=[0.1, 0.2],
                tags=[],
            ),
            MemoryEntry(
                timestamp=datetime(2026, 2, 16, 10, 0),
                role="system",
                content="User visited SF last year",
                embedding=[0.3, 0.4],
                tags=[],
            ),
        ]
        memories[0].entry_id = "abc123"
        memories[1].entry_id = "xyz789"

        mock_memory_store.search.return_value = (memories, {"abc123": 0.95, "xyz789": 0.82}, {})

        result = ""
        async for chunk in forget_tool.execute_stream(query="San Francisco"):
            result += chunk

        assert "Found 2 memories" in result
        assert "abc123" in result
        assert "xyz789" in result
        mock_memory_store.delete_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_no_results(self, forget_tool, mock_memory_store):
        """Query mode handles no matches gracefully."""
        mock_memory_store.search.return_value = ([], [], {})

        result = ""
        async for chunk in forget_tool.execute_stream(query="nonexistent"):
            result += chunk

        assert "No memories found" in result
        mock_memory_store.delete_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_truncates_long_content(self, forget_tool, mock_memory_store):
        """Query mode truncates long content."""
        memories = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17),
                role="system",
                content="A" * 100,
                embedding=[0.1, 0.2],
                tags=[],
            ),
        ]
        memories[0].entry_id = "long123"
        mock_memory_store.search.return_value = (memories, {"long123": 0.95}, {})

        result = ""
        async for chunk in forget_tool.execute_stream(query="test"):
            result += chunk

        assert "long123" in result
        assert "..." in result


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test suite for error handling."""

    @pytest.mark.asyncio
    async def test_memory_store_not_initialized(self):
        """Error when memory store not set."""
        tool = ForgetTool()

        result = ""
        async for chunk in tool.execute_stream(memory_id="abc123"):
            result += chunk

        assert "Error" in result
        assert "not initialized" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_memory_id(self, forget_tool, mock_memory_store):
        """Error for invalid memory_id."""
        mock_memory_store.get_by_id.return_value = None

        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="invalid"):
            result += chunk

        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_missing_parameters(self, forget_tool):
        """Error when neither memory_id nor query provided."""
        result = ""
        async for chunk in forget_tool.execute_stream():
            result += chunk

        assert "Error" in result
        assert "memory_id" in result.lower() or "query" in result.lower()

    @pytest.mark.asyncio
    async def test_query_error_handling(self, forget_tool, mock_memory_store):
        """Handles errors during query gracefully."""
        mock_memory_store.search.side_effect = Exception("Search failed")

        result = ""
        async for chunk in forget_tool.execute_stream(query="test"):
            result += chunk

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_get_by_id_error_handling(self, forget_tool, mock_memory_store):
        """Handles errors during get_by_id gracefully."""
        mock_memory_store.get_by_id.side_effect = Exception("DB error")

        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="test"):
            result += chunk

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_delete_error_handling(self, forget_tool, mock_memory_store, sample_memory):
        """Handles errors during delete gracefully."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory
        mock_memory_store.delete_by_id.side_effect = Exception("Delete failed")

        # First call
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass

        # Second call
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="abc123"):
            result += chunk

        assert "Error" in result


# ============================================================================
# Integration Scenario Tests
# ============================================================================


class TestIntegrationScenarios:
    """Test suite for end-to-end scenarios."""

    @pytest.mark.asyncio
    async def test_full_workflow_query_then_delete(self, forget_tool, mock_memory_store):
        """Full workflow: query finds candidates, then delete by ID."""
        memories = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17),
                role="system",
                content="User lives in San Francisco",
                embedding=[0.1, 0.2],
                tags=[],
            ),
        ]
        memories[0].entry_id = "sf-memory-id"
        mock_memory_store.search.return_value = (memories, {"sf-memory-id": 0.95}, {})
        mock_memory_store.get_by_id.return_value = memories[0]
        mock_memory_store.delete_by_id.return_value = (True, "Memory deleted")

        # Step 1: Query to find candidates
        result = ""
        async for chunk in forget_tool.execute_stream(query="San Francisco"):
            result += chunk
        assert "sf-memory-id" in result

        # Step 2: First call to mark for deletion
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="sf-memory-id"):
            result += chunk
        assert "Please confirm" in result

        # Step 3: Second call to execute deletion
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="sf-memory-id"):
            result += chunk
        assert "deleted" in result.lower()
        mock_memory_store.delete_by_id.assert_called_once_with("sf-memory-id")

    @pytest.mark.asyncio
    async def test_user_changes_mind_after_first_call(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """User can change mind - different ID on second call starts new request."""
        sample_memory.entry_id = "abc123"
        other_memory = MemoryEntry(
            timestamp=datetime(2026, 2, 16),
            role="system",
            content="Different memory",
            embedding=[0.3, 0.4],
            tags=[],
        )
        other_memory.entry_id = "xyz789"

        mock_memory_store.get_by_id.side_effect = [sample_memory, other_memory]

        # First call with abc123
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="abc123"):
            result += chunk
        assert "abc123" in forget_tool._pending_deletions

        # User changes mind, requests xyz789 instead
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="xyz789"):
            result += chunk

        assert "xyz789" in forget_tool._pending_deletions
        assert "Please confirm" in result
