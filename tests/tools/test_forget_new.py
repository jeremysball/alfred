"""Tests for forget tool with ID-based deletion and call-tracking confirmation (PRD #56)."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from src.tools.forget import ForgetTool, PendingDeletion
from src.types import MemoryEntry

# ============================================================================
# PendingDeletion Dataclass Tests
# ============================================================================


class TestPendingDeletion:
    """Test suite for PendingDeletion dataclass."""

    def test_pending_deletion_creation(self):
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

    def test_pending_deletion_defaults(self):
        """PendingDeletion uses sensible defaults."""
        now = datetime.now()
        pending = PendingDeletion(
            memory_id="abc123",
            content_preview="Test content",
            requested_at=now,
        )

        assert pending.request_count == 1  # Default to 1


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def mock_memory_store():
    """Create a mock memory store with async methods."""
    store = Mock()
    store.search = AsyncMock()
    store.get_by_id = AsyncMock()
    store.delete_by_id = AsyncMock()
    return store


@pytest_asyncio.fixture
async def forget_tool(mock_memory_store):
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
    async def test_different_id_treats_as_new_request(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """Second call with different memory_id treats as new first call."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory

        # First call with abc123
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass

        # Second call with xyz789
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="xyz789"):
            result += chunk

        assert "Please confirm" in result
        assert "xyz789" in forget_tool._pending_deletions
        assert "abc123" in forget_tool._pending_deletions  # Old one still there
        mock_memory_store.delete_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_count_increments(self, forget_tool, mock_memory_store, sample_memory):
        """Request count increments on each call before deletion executes."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory
        mock_memory_store.delete_by_id.return_value = (True, "Deleted")

        # First call - creates pending, count = 1
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        assert forget_tool._pending_deletions["abc123"].request_count == 1

        # Second call - increments to 2, executes deletion, clears pending
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        # Pending is cleared after successful deletion
        assert "abc123" not in forget_tool._pending_deletions

        # Third call - starts fresh, creates new pending with count = 1
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        assert forget_tool._pending_deletions["abc123"].request_count == 1

    @pytest.mark.asyncio
    async def test_deletion_requires_exactly_two_calls(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """Deletion only happens on second+ call with same ID."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory
        mock_memory_store.delete_by_id.return_value = (True, "Deleted")

        # First call - no deletion
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        mock_memory_store.delete_by_id.assert_not_called()

        # Second call - deletion executes
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        mock_memory_store.delete_by_id.assert_called_once()


# ============================================================================
# Query Mode Tests (Candidate Discovery)
# ============================================================================


class TestQueryMode:
    """Test suite for query-based candidate discovery."""

    @pytest.mark.asyncio
    async def test_query_returns_candidates(self, forget_tool, mock_memory_store):
        """Query mode returns list of candidates without deleting."""
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
                content="User visited San Francisco last year",
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

        assert "Found" in result or "Candidates" in result
        assert "abc123" in result
        assert "xyz789" in result
        assert "95%" in result or "95" in result
        assert "82%" in result or "82" in result
        mock_memory_store.delete_by_id.assert_not_called()
        mock_memory_store.search.assert_called_once_with("San Francisco", top_k=10)

    @pytest.mark.asyncio
    async def test_query_no_results(self, forget_tool, mock_memory_store):
        """Query mode handles no matches gracefully."""
        mock_memory_store.search.return_value = ([], [], {})

        result = ""
        async for chunk in forget_tool.execute_stream(query="nonexistent"):
            result += chunk

        assert "No memories found" in result or "not found" in result.lower()
        mock_memory_store.delete_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_shows_ids_for_selection(self, forget_tool, mock_memory_store):
        """Query results include memory IDs for user selection."""
        memories = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17),
                role="system",
                content="Test memory",
                embedding=[0.1, 0.2],
                tags=[],
            ),
        ]
        memories[0].entry_id = "test-id-123"
        mock_memory_store.search.return_value = (memories, {"test-id-123": 0.9}, {})

        result = ""
        async for chunk in forget_tool.execute_stream(query="test"):
            result += chunk

        assert "test-id-123" in result
        assert "ID" in result or "id" in result


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

        # First call - create pending
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass

        # Manually expire the pending deletion (simulate time passing)
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

    @pytest.mark.asyncio
    async def test_expiration_updates_timestamp(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """Expired pending gets new timestamp on re-request."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory

        # First call
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass

        old_time = forget_tool._pending_deletions["abc123"].requested_at

        # Expire it
        forget_tool._pending_deletions["abc123"].requested_at = datetime.now() - timedelta(
            minutes=6
        )

        # Second call (expired, so treats as new first call)
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass

        new_time = forget_tool._pending_deletions["abc123"].requested_at
        assert new_time > old_time


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_memory_already_deleted_between_calls(
        self, forget_tool, mock_memory_store, sample_memory
    ):
        """Handles memory deletion between first and second call."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.side_effect = [sample_memory, None]
        mock_memory_store.delete_by_id.return_value = (False, "Memory not found")

        # First call
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass

        # Second call - memory gone
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="abc123"):
            result += chunk

        assert "not found" in result.lower() or "already deleted" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_memory_id(self, forget_tool, mock_memory_store):
        """Handles invalid memory_id gracefully."""
        mock_memory_store.get_by_id.return_value = None

        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="invalid-id"):
            result += chunk

        assert "not found" in result.lower()
        mock_memory_store.delete_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_parameters(self, forget_tool):
        """Error when neither memory_id nor query provided."""
        result = ""
        async for chunk in forget_tool.execute_stream():
            result += chunk

        assert "Error" in result
        assert "memory_id" in result.lower() or "query" in result.lower()

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
    async def test_get_by_id_error_handling(self, forget_tool, mock_memory_store):
        """Handles errors during get_by_id gracefully."""
        mock_memory_store.get_by_id.side_effect = Exception("Database error")

        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="abc123"):
            result += chunk

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_delete_error_handling(self, forget_tool, mock_memory_store, sample_memory):
        """Handles errors during deletion gracefully."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory
        mock_memory_store.delete_by_id.side_effect = Exception("Delete failed")

        # First call
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass

        # Second call - delete fails
        result = ""
        async for chunk in forget_tool.execute_stream(memory_id="abc123"):
            result += chunk

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_query_error_handling(self, forget_tool, mock_memory_store):
        """Handles errors during query gracefully."""
        mock_memory_store.search.side_effect = Exception("Search failed")

        result = ""
        async for chunk in forget_tool.execute_stream(query="test"):
            result += chunk

        assert "Error" in result


# ============================================================================
# Tool Interface Tests
# ============================================================================


class TestToolInterface:
    """Test suite for tool interface and metadata."""

    def test_tool_name(self):
        """Tool has correct name."""
        tool = ForgetTool()
        assert tool.name == "forget"

    def test_tool_description_explains_two_call_pattern(self):
        """Tool description explains the two-call pattern clearly."""
        tool = ForgetTool()
        desc = tool.description.lower()

        # Should mention two calls or confirmation pattern
        assert "two" in desc or "confirm" in desc or "twice" in desc
        assert "delete" in desc

    def test_no_confirm_parameter(self):
        """Tool does not have confirm parameter."""
        tool = ForgetTool()
        params = tool.param_model.model_fields

        assert "confirm" not in params

    def test_has_memory_id_parameter(self):
        """Tool has memory_id parameter."""
        tool = ForgetTool()
        params = tool.param_model.model_fields

        assert "memory_id" in params or "entry_id" in params

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

        # Should create new pending for xyz789, abc123 still there
        assert "xyz789" in forget_tool._pending_deletions
        assert "Please confirm" in result

    @pytest.mark.asyncio
    async def test_rapid_successive_calls(self, forget_tool, mock_memory_store, sample_memory):
        """Multiple rapid calls execute deletion on 2nd call, then start fresh."""
        sample_memory.entry_id = "abc123"
        mock_memory_store.get_by_id.return_value = sample_memory
        mock_memory_store.delete_by_id.return_value = (True, "Deleted")

        # Call 1: Creates pending, count = 1
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        assert forget_tool._pending_deletions["abc123"].request_count == 1
        mock_memory_store.delete_by_id.assert_not_called()

        # Call 2: Executes deletion, clears pending
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        assert "abc123" not in forget_tool._pending_deletions
        assert mock_memory_store.delete_by_id.call_count == 1

        # Call 3: Starts fresh, creates new pending
        async for _ in forget_tool.execute_stream(memory_id="abc123"):
            pass
        assert forget_tool._pending_deletions["abc123"].request_count == 1
        assert mock_memory_store.delete_by_id.call_count == 1  # No new deletion
