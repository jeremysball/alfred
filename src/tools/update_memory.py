"""Tool for updating existing memories in the unified memory store."""

from collections.abc import AsyncIterator

from .base import Tool


class UpdateMemoryTool(Tool):
    """Update an existing memory's content or importance. Requires confirmation."""

    name = "update_memory"
    description = "Update an existing memory's content or importance. Requires confirmation."

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
        confirm: bool = False,
    ) -> str:
        """Update a memory (sync wrapper - use execute_stream).

        Args:
            search_query: Query to find the memory to update
            new_content: New content for the memory (empty = no change)
            new_importance: New importance value 0.0-1.0 (-1 = no change)
            confirm: Set to True to actually update. False = preview only.

        Returns:
            Error message directing to use async method
        """
        return "Error: UpdateMemoryTool must be called via execute_stream in async context"

    async def execute_stream(
        self,
        search_query: str,
        new_content: str = "",
        new_importance: float = -1,
        confirm: bool = False,
    ) -> AsyncIterator[str]:
        """Update a memory or show preview.

        Args:
            search_query: Query to find the memory to update
            new_content: New content for the memory (empty = no change)
            new_importance: New importance value 0.0-1.0 (-1 = no change)
            confirm: Set to True to actually update. False = preview only.

        Yields:
            Preview of memory to update, or update confirmation
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

        if not confirm:
            # Preview mode: search but don't update
            try:
                results = await self._memory_store.search(search_query, top_k=1)
                if not results:
                    yield f"No memory found matching '{search_query}'."
                    return

                entry = results[0]
                date_str = entry.timestamp.strftime("%Y-%m-%d")

                lines = ["Found memory to update:"]
                lines.append(f"  Current: [{date_str}] {entry.content}")
                lines.append(f"  Importance: {entry.importance:.1f}")
                lines.append("")
                lines.append("Will update to:")
                if content is not None:
                    lines.append(f"  New content: {content}")
                if importance is not None:
                    lines.append(f"  New importance: {importance:.1f}")
                lines.append("")
                lines.append(
                    f"Call update_memory(search_query='{search_query}', "
                    f"new_content='{new_content}', "
                    f"new_importance={new_importance}, confirm=True) to apply changes."
                )
                yield "\n".join(lines)
            except Exception as e:
                yield f"Error previewing update: {e}"
            return

        # Confirmed: actually update
        try:
            success, message = await self._memory_store.update_entry(
                search_query=search_query,
                new_content=content,
                new_importance=importance,
            )
            yield message
        except Exception as e:
            yield f"Error updating memory: {e}"
