"""Tool for saving memories to the unified memory store."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from alfred.memory import MemoryEntry

from .base import Tool
from .mixins import ContentTruncationMixin, MemoryStoreMixin, TagParsingMixin


class RememberToolParams(BaseModel):
    """Parameters for RememberTool."""

    content: str = Field(..., description="The distilled insight or fact to remember")
    tags: str = Field("", description="Comma-separated list of category tags")
    permanent: bool = Field(False, description="Mark as permanent (skip 90-day TTL)")

    class Config:
        extra = "forbid"


class RememberTool(Tool, MemoryStoreMixin, TagParsingMixin, ContentTruncationMixin):
    """Save a memory to the unified memory store.

    Use this when the user asks you to remember something,
    or when you learn important facts, preferences, or context
    that would be useful to recall in future conversations.
    """

    name = "remember"
    description = (
        "Save a curated memory to the unified memory store for future retrieval. "
        "Prefer selective, high-value memories over transient noise."
    )
    param_model = RememberToolParams

    def __init__(self, memory_store: Any = None) -> None:
        Tool.__init__(self)
        MemoryStoreMixin.__init__(self, memory_store)

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Save a memory to the unified store (async)."""
        content = kwargs.get("content", "")
        tags = kwargs.get("tags", "")
        permanent = kwargs.get("permanent", False)

        if not self._memory_store:
            yield "Error: Memory store not initialized"
            return

        tag_list = self._parse_tags(tags)

        entry = MemoryEntry(
            entry_id=str(uuid4()),
            timestamp=datetime.now(),
            role="system",
            content=content,
            embedding=None,
            tags=tag_list,
            permanent=permanent,
        )

        try:
            await self._memory_store.add_entries([entry])
            tag_str = self._format_tags(tag_list)
            perm_str = " [permanent]" if permanent else ""
            truncated = self._truncate(content)
            result = f"Remembered: {truncated}{tag_str}{perm_str}"
            yield result
        except Exception as e:
            yield f"Error saving memory: {e}"
