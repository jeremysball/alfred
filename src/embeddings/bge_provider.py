"""BGE (BAAI General Embedding) local embedding provider.

Uses sentence-transformers to run BGE models locally.
Implements singleton pattern for model loading.
"""

import asyncio
import logging
from typing import Protocol, TypedDict, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from src.embeddings.provider import EmbeddingProvider

logger = logging.getLogger(__name__)

type EmbeddingArray = NDArray[np.float32]


class ModelConfig(TypedDict):
    model_id: str
    dimension: int


@runtime_checkable
class SentenceTransformerProtocol(Protocol):
    def encode(
        self,
        texts: str | list[str],
        normalize_embeddings: bool = ...,
    ) -> EmbeddingArray:
        ...


# Singleton model instance
_model_instance: SentenceTransformerProtocol | None = None
_model_name: str | None = None

# Model configurations
MODEL_CONFIGS: dict[str, ModelConfig] = {
    "bge-small": {
        "model_id": "BAAI/bge-small-en-v1.5",
        "dimension": 384,
    },
    "bge-base": {
        "model_id": "BAAI/bge-base-en-v1.5",
        "dimension": 768,
    },
    "bge-large": {
        "model_id": "BAAI/bge-large-en-v1.5",
        "dimension": 1024,
    },
}


def get_model(model_name: str = "bge-base") -> SentenceTransformerProtocol:
    """Get or create singleton SentenceTransformer model.

    Args:
        model_name: Model variant (bge-small, bge-base, bge-large)

    Returns:
        SentenceTransformer model instance
    """
    global _model_instance, _model_name

    if _model_instance is None or _model_name != model_name:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers not installed. Install with: uv add sentence-transformers"
            ) from e

        config = MODEL_CONFIGS.get(model_name, MODEL_CONFIGS["bge-base"])
        model_id = str(config["model_id"])

        logger.info(f"Loading embedding model: {model_id}")
        model = SentenceTransformer(model_id)
        if not isinstance(model, SentenceTransformerProtocol):
            raise TypeError("SentenceTransformer does not implement encode()")
        _model_instance = model
        _model_name = model_name
        logger.info(f"Model loaded successfully: {model_id}")

    if _model_instance is None:
        raise RuntimeError("Embedding model failed to load")
    return _model_instance


class BGEProvider(EmbeddingProvider):
    """Local embedding provider using BGE models.

    Features:
    - Runs locally (no API calls)
    - 768-dimensional embeddings (bge-base)
    - ~52ms query latency
    - Free (no API costs)
    """

    def __init__(self, model_name: str = "bge-base") -> None:
        """Initialize BGE provider.

        Args:
            model_name: Model variant (bge-small, bge-base, bge-large)
        """
        self._model_name = model_name
        self._config: ModelConfig = MODEL_CONFIGS.get(
            model_name,
            MODEL_CONFIGS["bge-base"],
        )
        self._model = get_model(model_name)

    @property
    def dimension(self) -> int:
        """Return embedding dimension based on model."""
        return int(self._config["dimension"])

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        # Run in thread pool since SentenceTransformer is synchronous
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            self._embed_sync,
            text,
        )
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Run in thread pool since SentenceTransformer is synchronous
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self._embed_batch_sync,
            texts,
        )
        return embeddings

    def _embed_sync(self, text: str) -> list[float]:
        """Synchronous embedding (called from thread pool)."""

        embedding = self._model.encode(text, normalize_embeddings=True)
        return [float(value) for value in embedding]

    def _embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding (called from thread pool)."""
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return [[float(value) for value in row] for row in embeddings]
