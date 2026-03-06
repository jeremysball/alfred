"""Base memory types and interfaces."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class MemoryEntry:
    """A single memory entry with content and metadata.
    
    This replaces the old MemoryEntry from jsonl_store.
    """

    entry_id: str
    content: str
    timestamp: datetime
    role: Literal["user", "assistant", "system"] = "assistant"
    embedding: list[float] | None = None
    tags: list[str] = field(default_factory=list)
    permanent: bool = False

    def __hash__(self) -> int:
        """Make MemoryEntry hashable for deduplication."""
        return hash(self.entry_id)

    def __eq__(self, other: object) -> bool:
        """Equality based on entry_id."""
        if not isinstance(other, MemoryEntry):
            return NotImplemented
        return self.entry_id == other.entry_id


class MemoryStore:
    """Abstract base class for memory storage backends."""

    async def add(self, entry: MemoryEntry) -> None:
        """Add a memory entry."""
        raise NotImplementedError

    async def get(self, entry_id: str) -> MemoryEntry | None:
        """Get a memory by ID."""
        raise NotImplementedError

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[MemoryEntry]:
        """Search memories by vector similarity."""
        raise NotImplementedError

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory by ID."""
        raise NotImplementedError
