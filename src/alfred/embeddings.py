"""OpenAI embedding client - DEPRECATED.

This module is deprecated. Use src.embeddings package instead:
    from alfred.embeddings import EmbeddingProvider, BGEProvider, OpenAIProvider
    from alfred.embeddings import cosine_similarity, create_provider

For backward compatibility, this module re-exports the OpenAIProvider
and cosine_similarity function.
"""

import warnings

# Re-export from new package for backward compatibility
from alfred.embeddings import cosine_similarity
from alfred.embeddings.openai_provider import (
    EmbeddingError,
    OpenAIProvider,
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
