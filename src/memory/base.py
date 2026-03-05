"""Base class for memory stores."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal


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
    async def add(self, entry: Any) -> None:
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
        **kwargs
    ) -> tuple[list[Any], dict[str, float], dict[str, float]]:
        """Search memories by semantic similarity.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            Tuple of (results, similarities, scores)
        """
        ...
    
    @abstractmethod
    async def get_by_id(self, entry_id: str) -> Any | None:
        """Get memory by ID.
        
        Args:
            entry_id: Unique memory ID
            
        Returns:
            Memory entry or None
        """
        ...
    
    @abstractmethod
    async def get_all_entries(self) -> list[Any]:
        """Get all memory entries.
        
        Returns:
            List of all entries
        """
        ...
    
    @abstractmethod
    async def delete_by_id(self, entry_id: str) -> tuple[bool, str]:
        """Delete memory by ID.
        
        Args:
            entry_id: Unique memory ID
            
        Returns:
            Tuple of (success, message)
        """
        ...
