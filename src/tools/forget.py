"""Tool for deleting memories from the unified memory store."""

from collections.abc import AsyncIterator

from .base import Tool


class ForgetTool(Tool):
    """Delete memories matching a semantic query. Requires confirmation."""

    name = "forget"
    description = "Delete memories matching a semantic query. Requires confirmation."

    def __init__(self, memory_store=None):
        super().__init__()
        self._memory_store = memory_store

    def set_memory_store(self, memory_store):
        """Set the memory store after initialization."""
        self._memory_store = memory_store

    def execute(
        self,
        query: str = "",
        entry_id: str = "",
        confirm: bool = False,
    ) -> str:
        """Delete memories (sync wrapper - use execute_stream).

        Args:
            query: Semantic query to find memories to delete (use entry_id or this)
            entry_id: Direct delete by memory ID (use this or query)
            confirm: Set to True to actually delete. False = preview only.

        Returns:
            Error message directing to use async method
        """
        return "Error: ForgetTool must be called via execute_stream in async context"

    async def execute_stream(
        self,
        query: str = "",
        entry_id: str = "",
        confirm: bool = False,
    ) -> AsyncIterator[str]:
        """Delete memories or show preview.

        Args:
            query: Semantic query to find memories to delete
            entry_id: Direct delete by memory ID
            confirm: Set to True to actually delete. False = preview only.

        Yields:
            Preview of memories to delete, or deletion confirmation
        """
        if not self._memory_store:
            yield "Error: Memory store not initialized"
            return

        # Must provide one of query or entry_id
        if not query and not entry_id:
            yield "Error: Provide either query or entry_id"
            return

        if not confirm:
            # Preview mode: find but don't delete
            try:
                if entry_id:
                    entry = await self._memory_store.get_by_id(entry_id)
                    if not entry:
                        yield f"No memory found with ID: {entry_id}"
                        return
                    
                    date_str = entry.timestamp.strftime("%Y-%m-%d")
                    lines = ["Found memory to delete:"]
                    lines.append(f"  - [{date_str}] {entry.content[:60]}...")
                    lines.append(f"  ID: {entry.entry_id}")
                    lines.append("")
                    lines.append(
                        f"Call forget(entry_id='{entry_id}', confirm=True) to delete this memory."
                    )
                    yield "\n".join(lines)
                else:
                    results = await self._memory_store.search(query, top_k=100)
                    if not results:
                        yield f"No memories found matching '{query}'."
                        return

                    # Format preview
                    lines = [f"Found {len(results)} memories matching '{query}':"]
                    for entry in results[:5]:  # Show first 5
                        date_str = entry.timestamp.strftime("%Y-%m-%d")
                        preview = entry.content[:60]
                        if len(entry.content) > 60:
                            preview += "..."
                        lines.append(f"  - [{date_str}] {preview} (id: {entry.entry_id})")

                    if len(results) > 5:
                        lines.append(f"  ... and {len(results) - 5} more")

                    lines.append("")
                    lines.append(
                        f"Call forget(query='{query}', confirm=True) to delete these memories."
                    )
                    yield "\n".join(lines)
            except Exception as e:
                yield f"Error previewing memories: {e}"
            return

        # Confirmed: actually delete
        try:
            if entry_id:
                success, message = await self._memory_store.delete_by_id(entry_id)
                yield message
            else:
                count, message = await self._memory_store.delete_entries(query)
                yield message
        except Exception as e:
            yield f"Error deleting memories: {e}"
