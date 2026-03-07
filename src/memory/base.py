"""Base class for memory stores."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from src.type_defs import MemoryEntryLike


@dataclass
class MemoryMetadata:
    """Memory entry metadata (stored separately from embeddings)."""

    entry_id: str
    timestamp: datetime
    role: Literal["user", "assistant", "system"]
    content: str
    tags: list[str]
    permanent: bool = False


class MemoryStore(ABC):
    """Abstract base class for memory storage backends.

    All memory stores must implement:
    - add(): Add a memory entry
    - search(): Search by semantic similarity
    - get_by_id(): Direct lookup by ID
    - get_all_entries(): Get all entries
    - delete(): Delete by ID or query
    """

    @abstractmethod
    async def add(self, entry: MemoryEntryLike) -> None:
        """Add a memory entry.

        Args:
            entry: MemoryEntry to add
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs: object,
    ) -> tuple[list[MemoryEntryLike], dict[str, float], dict[str, float]]:
        """Search memories by semantic similarity.

        Args:
            query: Search query text
            top_k: Number of results to return

        Returns:
            Tuple of (results, similarities, scores)
        """
        ...

    @abstractmethod
    async def get_by_id(self, entry_id: str) -> MemoryEntryLike | None:
        """Get memory by ID.

        Args:
            entry_id: Unique memory ID

        Returns:
            Memory entry or None
        """
        ...

    @abstractmethod
    async def get_all_entries(self) -> list[MemoryEntryLike]:
        """Get all memory entries.

        Returns:
            List of all entries
        """
        ...

    async def update_entry(
        self,
        search_query: str,
        new_content: str | None = None,
    ) -> tuple[bool, str]:
        """Update an existing memory entry.

        Override in stores that support updating entries.
        """
        raise NotImplementedError("update_entry is not supported by this store")

    @abstractmethod
    async def delete_by_id(self, entry_id: str) -> tuple[bool, str]:
        """Delete memory by ID.

        Args:
            entry_id: Unique memory ID

        Returns:
            Tuple of (success, message)
        """
        ...
