"""OpenAI embedding client - DEPRECATED.

This module is deprecated. Use src.embeddings package instead:
    from src.embeddings import EmbeddingProvider, BGEProvider, OpenAIProvider
    from src.embeddings import cosine_similarity, create_provider

For backward compatibility, this module re-exports the OpenAIProvider
and cosine_similarity function.
"""

import warnings

# Re-export from new package for backward compatibility
from src.embeddings import cosine_similarity
from src.embeddings.openai_provider import (
    EmbeddingClient as OpenAIProvider,
)
from src.embeddings.openai_provider import (
    EmbeddingError,
    _is_transient_error,
    _with_retry,
)

warnings.warn(
    "src.embeddings is deprecated. Use src.embeddings package instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "cosine_similarity",
    "EmbeddingClient",
    "EmbeddingError",
    "_is_transient_error",
    "_with_retry",
    # Keep old name for compatibility
    "OpenAIProvider",
]

# Alias for backward compatibility
EmbeddingClient = OpenAIProvider
