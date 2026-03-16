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
        query: str,
        top_k: int = 10,
    ) -> tuple[list[MemoryEntry], dict[str, float], dict[str, float]]:
        """Search memories by vector similarity.

        Args:
            query: Search query text (implementations handle embedding generation)
            top_k: Maximum number of results to return

        Returns:
            Tuple of (entries, similarities, scores) where:
                - entries: List of matching MemoryEntry objects
                - similarities: Dict mapping entry_id to similarity score
                - scores: Dict mapping entry_id to score
        """
        raise NotImplementedError

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory by ID."""
        raise NotImplementedError

    async def get_all_entries(self) -> list[MemoryEntry]:
        """Get all memory entries.

        Returns:
            List of all MemoryEntry objects in the store.
        """
        raise NotImplementedError
