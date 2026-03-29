"""Tool for searching memories in the unified memory store."""

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .base import Tool
from .mixins import ErrorHandlingMixin, MemoryStoreMixin, SearchResultMixin


class SearchMemoriesToolParams(BaseModel):
    """Parameters for SearchMemoriesTool."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field("", description="Search query to find relevant memories")
    entry_id: str = Field("", description="Direct lookup by memory ID")
    top_k: int = Field(5, description="Maximum number of results to return")


class SearchMemoriesTool(Tool, MemoryStoreMixin, SearchResultMixin, ErrorHandlingMixin):
    """Search through saved memories for relevant information."""

    name = "search_memories"
    description = (
        "Search curated memories for durable facts, preferences, and prior context. "
        "Use before asking the user to repeat themselves."
    )
    param_model = SearchMemoriesToolParams

    def __init__(self, memory_store: Any = None) -> None:
        Tool.__init__(self)
        MemoryStoreMixin.__init__(self, memory_store)

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Search memories and return formatted results."""
        query = kwargs.get("query", "")
        entry_id = kwargs.get("entry_id", "")
        top_k = kwargs.get("top_k", 5)

        if not self._memory_store:
            yield "Error: Memory store not initialized"
            return

        if entry_id:
            try:
                entry = await self._memory_store.get_by_id(entry_id)
                if not entry:
                    yield f"No memory found with ID: {entry_id}"
                    return
                yield self._format_entry(entry)
                return
            except Exception as e:
                yield f"Error retrieving memory: {e}"
                return

        if not query:
            yield "Error: Provide either query or entry_id"
            return

        try:
            results, similarities, scores = await self._memory_store.search(query, top_k=top_k)
            yield self._format_results(results, similarities, scores)
        except Exception as e:
            yield f"Error searching memories: {e}"
