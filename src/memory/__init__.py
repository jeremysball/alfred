"""Memory storage backends for Alfred.

Supports multiple storage backends:
- JSONL (legacy, linear scan)
- FAISS (ANN index, 5,400x faster search)
"""

from src.memory.base import MemoryStore, MemoryMetadata
from src.memory.jsonl_store import JSONLMemoryStore

__all__ = [
    "MemoryStore",
    "MemoryMetadata", 
    "JSONLMemoryStore",
    "create_memory_store",
]

# FAISS store is optional (requires faiss-cpu)
try:
    from src.memory.faiss_store import FAISSMemoryStore
    __all__.append("FAISSMemoryStore")
except ImportError:
    FAISSMemoryStore = None  # type: ignore


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
        if FAISSMemoryStore is None:
            raise ImportError(
                "FAISS memory store requested but faiss-cpu not installed. "
                "Install with: uv add faiss-cpu"
            )
        return FAISSMemoryStore(
            index_path=memory_dir or config.memory_dir / "faiss",
            provider=embedder,
        )
    else:
        # Import here to avoid circular dependency
        from src.memory import JSONLMemoryStore
        return JSONLMemoryStore(
            config=config,
            embedder=embedder,
        )
