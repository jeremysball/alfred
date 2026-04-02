"""Memory storage backends for Alfred.

Uses SQLite + sqlite-vec for unified storage with vector search.
"""

from alfred.config import Config
from alfred.embeddings.provider import EmbeddingProvider
from alfred.memory.base import MemoryEntry, MemoryStore
from alfred.memory.sqlite_store import SQLiteMemoryStore
from alfred.memory.support_memory import EvidenceRef, SupportEpisode

# Re-export for compatibility
__all__ = [
    "EvidenceRef",
    "MemoryEntry",
    "MemoryStore",
    "SQLiteMemoryStore",
    "SupportEpisode",
    "create_memory_store",
]


def create_memory_store(config: Config, embedder: EmbeddingProvider) -> SQLiteMemoryStore:
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
