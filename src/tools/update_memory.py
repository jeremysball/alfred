"""Tool for updating existing memories in the unified memory store."""

from collections.abc import AsyncIterator

from .base import Tool


class UpdateMemoryTool(Tool):
    """Update an existing memory's content or importance."""

    name = "update_memory"
    description = "Update an existing memory's content or importance"

    def __init__(self, memory_store=None):
        super().__init__()
        self._memory_store = memory_store

    def set_memory_store(self, memory_store):
        """Set the memory store after initialization."""
        self._memory_store = memory_store

    def execute(
        self,
        search_query: str,
        new_content: str = "",
        new_importance: float = -1,
    ) -> str:
        """Update a memory (sync wrapper - use execute_stream).

        Args:
            search_query: Query to find the memory to update
            new_content: New content for the memory (empty = no change)
            new_importance: New importance value 0.0-1.0 (-1 = no change)

        Returns:
            Error message directing to use async method
        """
        return "Error: UpdateMemoryTool must be called via execute_stream in async context"

    async def execute_stream(
        self,
        search_query: str,
        new_content: str = "",
        new_importance: float = -1,
    ) -> AsyncIterator[str]:
        """Update a memory and return result.

        Args:
            search_query: Query to find the memory to update
            new_content: New content for the memory (empty = no change)
            new_importance: New importance value 0.0-1.0 (-1 = no change)

        Yields:
            Result message
        """
        if not self._memory_store:
            yield "Error: Memory store not initialized"
            return

        # Convert empty string to None (no change)
        content = new_content if new_content else None
        # Convert -1 to None (no change)
        importance = new_importance if new_importance >= 0 else None

        if content is None and importance is None:
            yield "Error: Specify at least one of new_content or new_importance"
            return

        try:
            success, message = await self._memory_store.update_entry(
                search_query=search_query,
                new_content=content,
                new_importance=importance,
            )
            yield message
        except Exception as e:
            yield f"Error updating memory: {e}"
