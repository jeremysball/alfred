"""Tool for deleting memories with ID-based deletion and call-tracking confirmation."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from .base import Tool


@dataclass
class PendingDeletion:
    """Tracks a deletion request awaiting confirmation."""

    memory_id: str
    content_preview: str
    requested_at: datetime = field(default_factory=datetime.now)
    request_count: int = 1

    def is_expired(self, timeout_minutes: int = 5) -> bool:
        """Check if this pending deletion has expired."""
        return datetime.now() - self.requested_at > timedelta(minutes=timeout_minutes)


class ForgetToolParams(BaseModel):
    """Parameters for ForgetTool."""

    memory_id: str | None = Field(
        None,
        description=(
            "The exact ID of the memory to delete. "
            "Must be called twice with the same ID for deletion to occur."
        ),
    )
    query: str | None = Field(
        None,
        description=(
            "Search query to find memory candidates. Returns list with IDs. "
            "Use this to find the memory_id before deleting."
        ),
    )

    class Config:
        extra = "forbid"


class ForgetTool(Tool):
    """Delete a memory by its exact ID. This tool requires two calls to execute:

    1. First call: Provide memory_id to mark for deletion (confirmation requested)
    2. Second call: Provide the same memory_id again to execute deletion

    Alternatively, use query (without memory_id) to search for candidates.

    Examples:
    - Find candidates: forget(query="San Francisco") → returns list
    - Mark for deletion: forget(memory_id="abc123") → "Please confirm..."
    - Execute deletion: forget(memory_id="abc123") → "Deleted successfully"
    """

    name = "forget"
    description = (
        "Delete a memory by its exact ID. This tool requires two calls to execute: "
        "1) First call marks the memory for deletion and requests confirmation. "
        "2) Second call with the same memory_id executes the deletion. "
        "Alternatively, use 'query' to search for candidates without deleting."
    )
    param_model = ForgetToolParams

    def __init__(self, memory_store: Any = None) -> None:
        super().__init__()
        self._memory_store = memory_store
        self._pending_deletions: dict[str, PendingDeletion] = {}

    def set_memory_store(self, memory_store: Any) -> None:
        """Set the memory store after initialization."""
        self._memory_store = memory_store

    def execute(self, **kwargs: Any) -> str:
        """Sync execute returns error message.

        Args:
            **kwargs: Tool parameters (ignored in sync mode)

        Returns:
            Error message directing to use async method
        """
        return "Error: ForgetTool must be called via execute_stream in async context"

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Delete memories or show candidates.

        Args:
            **kwargs: Tool parameters including:
                - memory_id: The exact ID of the memory to delete. Must be called
                  twice with the same ID for deletion to occur.
                - query: Search query to find memory candidates. Returns list
                  with IDs. Use this to find the memory_id before deleting.

        Yields:
            - If query provided: List of candidates with IDs
            - If memory_id provided (first call): Confirmation request
            - If memory_id provided (second call): Deletion result
        """
        if not self._memory_store:
            yield "Error: Memory store not initialized"
            return

        memory_id: str | None = kwargs.get("memory_id")
        query: str | None = kwargs.get("query")

        # Must provide one of memory_id or query
        if not memory_id and not query:
            yield "Error: Provide either memory_id or query parameter"
            return

        # Query mode: return candidates without deleting
        if query and not memory_id:
            async for chunk in self._handle_query_mode(query):
                yield chunk
            return

        # Memory ID mode: two-call confirmation pattern
        if memory_id:
            async for chunk in self._handle_memory_id_mode(memory_id):
                yield chunk
            return

    async def _handle_query_mode(self, query: str) -> AsyncIterator[str]:
        """Handle query mode - search and return candidates."""
        try:
            results, similarities, _ = await self._memory_store.search(query, top_k=10)

            if not results:
                yield f"No memories found matching '{query}'."
                return

            lines = [f"Found {len(results)} memories matching '{query}':\n"]

            for entry in results:
                date_str = entry.timestamp.strftime("%Y-%m-%d")
                preview = entry.content[:60]
                if len(entry.content) > 60:
                    preview += "..."
                similarity = similarities.get(entry.entry_id, 0.0)
                match_pct = int(similarity * 100)
                lines.append(f"  - [{date_str}] {preview}")
                lines.append(f"    ID: {entry.entry_id} ({match_pct}% match)")

            lines.append('\nTo delete a memory, use: forget(memory_id="<id>")')
            yield "\n".join(lines)

        except Exception as e:
            yield f"Error searching memories: {e}"

    async def _handle_memory_id_mode(self, memory_id: str) -> AsyncIterator[str]:
        """Handle memory ID mode - two-call confirmation pattern."""
        # Check if this ID is already pending
        if memory_id in self._pending_deletions:
            pending = self._pending_deletions[memory_id]

            # Check if expired
            if pending.is_expired():
                # Expired - reset as new request
                pending.request_count = 1
                pending.requested_at = datetime.now()
                yield await self._request_confirmation(memory_id)
                return

            # Not expired - increment count and check if should execute
            pending.request_count += 1

            if pending.request_count >= 2:
                # Second+ call - execute deletion
                async for chunk in self._execute_deletion(memory_id):
                    yield chunk
                return
            else:
                # Still need more calls
                yield await self._request_confirmation(memory_id)
                return
        else:
            # First call - create pending and request confirmation
            yield await self._request_confirmation(memory_id)

    async def _request_confirmation(self, memory_id: str) -> str:
        """Create pending deletion and return confirmation message."""
        try:
            entry = await self._memory_store.get_by_id(memory_id)

            if not entry:
                return f"Error: Memory not found with ID: {memory_id}"

            # Create or update pending
            if memory_id not in self._pending_deletions:
                preview = entry.content[:80]
                if len(entry.content) > 80:
                    preview += "..."
                self._pending_deletions[memory_id] = PendingDeletion(
                    memory_id=memory_id,
                    content_preview=preview,
                )
            else:
                # Update existing pending
                self._pending_deletions[memory_id].request_count += 1

            pending = self._pending_deletions[memory_id]
            date_str = entry.timestamp.strftime("%Y-%m-%d")

            return (
                f"Please confirm deletion:\n"
                f"  Memory: [{date_str}] {pending.content_preview}\n"
                f"  ID: {memory_id}\n\n"
                f"Call forget(memory_id='{memory_id}') again to confirm deletion."
            )

        except Exception as e:
            return f"Error retrieving memory: {e}"

    async def _execute_deletion(self, memory_id: str) -> AsyncIterator[str]:
        """Execute the actual deletion."""
        try:
            success, message = await self._memory_store.delete_by_id(memory_id)

            # Remove from pending regardless of success
            if memory_id in self._pending_deletions:
                del self._pending_deletions[memory_id]

            if success:
                yield f"✓ {message}"
            else:
                yield f"Error: {message}"

        except Exception as e:
            # Remove from pending on error too
            if memory_id in self._pending_deletions:
                del self._pending_deletions[memory_id]
            yield f"Error deleting memory: {e}"
