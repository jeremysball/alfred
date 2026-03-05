"""Memory storage backends for Alfred.

Supports multiple storage backends:
- JSONL (legacy, linear scan)
- FAISS (ANN index, 5,400x faster search)
"""

from src.memory.base import MemoryStore
from src.memory.faiss_store import FAISSMemoryStore, MemoryEntry

__all__ = [
    "MemoryStore",
    "MemoryEntry",
    "FAISSMemoryStore",
    "create_memory_store",
]

# JSONL store is optional (may not be needed if FAISS works well)
try:
    from src.memory.jsonl_store import JSONLMemoryStore
    __all__.append("JSONLMemoryStore")
except ImportError:
    JSONLMemoryStore = None  # type: ignore


def create_memory_store(config, embedder, memory_dir=None):
    """Create appropriate memory store based on config.

    Args:
        config: Application configuration
        embedder: Embedding provider instance
        memory_dir: Optional override for memory directory

    Returns:
        MemoryStore instance (FAISS or JSONL)
    """
    store_type = getattr(config, "memory_store", "jsonl")

    if store_type == "faiss":
        return FAISSMemoryStore(
            index_path=memory_dir or config.memory_dir / "faiss",
            provider=embedder,
            index_type=getattr(config, "faiss_index_type", "auto"),
        )
    else:
        # Fallback to JSONL (legacy)
        if JSONLMemoryStore is None:
            raise ImportError(
                "JSONL memory store requested but not available. "
                "Use memory_store='faiss' in config."
            )
        return JSONLMemoryStore(
            config=config,
            embedder=embedder,
        )
