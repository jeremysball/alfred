"""Memory storage backends for Alfred.

Uses SQLite + sqlite-vec for unified storage with vector search.
"""

from alfred.memory.base import MemoryEntry, MemoryStore
from alfred.memory.sqlite_store import SQLiteMemoryStore

# Re-export for compatibility
__all__ = [
    "MemoryEntry",
    "MemoryStore",
    "SQLiteMemoryStore",
    "create_memory_store",
]


def create_memory_store(config, embedder):
    """Create SQLite memory store.

    Args:
        config: Application configuration
        embedder: Embedding provider instance

    Returns:
        SQLiteMemoryStore instance
    """
    return SQLiteMemoryStore(
        config=config,
        embedder=embedder,
    )
