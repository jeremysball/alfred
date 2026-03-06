"""Memory storage backends for Alfred.

Uses SQLite + sqlite-vec for unified storage with vector search.
Legacy JSONL and FAISS stores are deprecated and will be removed.
"""

from src.memory.base import MemoryStore
from src.memory.sqlite_store import SQLiteMemoryStore

# Re-export for compatibility
__all__ = [
    "MemoryStore",
    "SQLiteMemoryStore",
    "create_memory_store",
]

# Legacy exports (deprecated, will be removed)
try:
    from src.memory.jsonl_store import JSONLMemoryStore, MemoryEntry
    __all__.extend(["JSONLMemoryStore", "MemoryEntry"])
except ImportError:
    pass

try:
    from src.memory.faiss_store import FAISSMemoryStore
    __all__.append("FAISSMemoryStore")
except ImportError:
    pass


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
