"""Embedding providers for Alfred memory system.

Supports multiple embedding backends:
- OpenAI (text-embedding-3-small) - default
- BGE-base (local, 768-dim) - faster, free, better quality
"""

from typing import TYPE_CHECKING

from src.embeddings.bge_provider import BGEProvider
from src.embeddings.openai_provider import OpenAIProvider
from src.embeddings.provider import EmbeddingProvider


# Provide EmbeddingClient alias for backwards compatibility
class EmbeddingClient:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("EmbeddingClient is deprecated. Use create_provider() instead.")

if TYPE_CHECKING:
    from src.config import Config

__all__ = [
    "EmbeddingProvider",
    "BGEProvider",
    "OpenAIProvider",
    "create_provider",
    "cosine_similarity",
]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def create_provider(config: "Config") -> EmbeddingProvider:
    """Create appropriate embedding provider based on config.

    Args:
        config: Application configuration

    Returns:
        EmbeddingProvider instance (BGE or OpenAI)
    """
    provider_type = getattr(config, "embedding_provider", "openai")

    if provider_type == "local":
        return BGEProvider(model_name=getattr(config, "local_embedding_model", "bge-base"))
    else:
        return OpenAIProvider(config)
