"""Memory storage backends for Alfred.

JSONL is the only supported memory store.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from src.memory.base import MemoryStore
from src.memory.jsonl_store import JSONLMemoryStore, MemoryEntry

if TYPE_CHECKING:
    from src.config import Config
    from src.embeddings.provider import EmbeddingProvider

__all__ = [
    "MemoryStore",
    "MemoryEntry",
    "JSONLMemoryStore",
    "create_memory_store",
]


def create_memory_store(
    config: "Config",
    embedder: "EmbeddingProvider",
    memory_dir: Path | None = None,
) -> MemoryStore:
    """Create JSONL memory store.

    Args:
        config: Application configuration
        embedder: Embedding provider instance
        memory_dir: Optional override for memory directory

    Returns:
        JSONLMemoryStore instance
    """
    if memory_dir is not None:
        config.memory_dir = memory_dir
    return JSONLMemoryStore(
        config=config,
        embedder=embedder,
    )
