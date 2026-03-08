"""BGE (BAAI General Embedding) local embedding provider.

Uses sentence-transformers to run BGE models locally.
Implements lazy async loading with singleton pattern.
"""

import asyncio
import logging
from typing import Any, TypedDict

from alfred.embeddings.provider import EmbeddingProvider

logger = logging.getLogger(__name__)

# Singleton model instance - loaded once, stays loaded forever
_model_instance: Any = None
_model_name: str | None = None
_model_lock: asyncio.Lock | None = None


class _ModelConfig(TypedDict):
    model_id: str
    dimension: int


# Model configurations
MODEL_CONFIGS: dict[str, _ModelConfig] = {
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


def _get_model_lock() -> asyncio.Lock:
    """Get or create the singleton lock for thread-safe model loading."""
    global _model_lock
    if _model_lock is None:
        _model_lock = asyncio.Lock()
    return _model_lock


async def _load_model_async(model_name: str = "bge-base") -> Any:
    """Load the SentenceTransformer model asynchronously.

    This runs the synchronous model loading in a thread pool to avoid
    blocking the event loop.

    Args:
        model_name: Model variant (bge-small, bge-base, bge-large)

    Returns:
        SentenceTransformer model instance
    """
    global _model_instance, _model_name

    async with _get_model_lock():
        # Double-check after acquiring lock
        if _model_instance is not None and _model_name == model_name:
            return _model_instance

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers not installed. Install with: uv add sentence-transformers"
            ) from e

        config = MODEL_CONFIGS.get(model_name, MODEL_CONFIGS["bge-base"])
        model_id = config["model_id"]

        logger.info(f"Loading embedding model: {model_id}")

        # Run synchronous model loading in thread pool
        loop = asyncio.get_event_loop()
        _model_instance = await loop.run_in_executor(
            None,
            lambda: SentenceTransformer(model_id)
        )
        _model_name = model_name

        logger.info(f"Model loaded successfully: {model_id}")
        return _model_instance


def get_model(model_name: str = "bge-base") -> Any:
    """Get or create singleton SentenceTransformer model (synchronous).

    NOTE: This is the synchronous version that blocks. Prefer using
    BGEProvider.initialize() or BGEProvider.embed() which load async.

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
        model_id = config["model_id"]

        logger.info(f"Loading embedding model: {model_id}")
        _model_instance = SentenceTransformer(model_id)
        _model_name = model_name
        logger.info(f"Model loaded successfully: {model_id}")

    return _model_instance


class BGEProvider(EmbeddingProvider):
    """Local embedding provider using BGE models.

    Features:
    - Runs locally (no API calls)
    - Lazy async loading - doesn't block startup
    - Model stays loaded forever (singleton)
    - 768-dimensional embeddings (bge-base)
    - ~52ms query latency
    - Free (no API costs)
    """

    def __init__(self, model_name: str = "bge-base") -> None:
        """Initialize BGE provider without loading the model.

        The model is loaded lazily on first embed() call or when
        initialize() is explicitly called.

        Args:
            model_name: Model variant (bge-small, bge-base, bge-large)
        """
        self._model_name = model_name
        self._config = MODEL_CONFIGS.get(model_name, MODEL_CONFIGS["bge-base"])
        self._model: Any | None = None

    @property
    def dimension(self) -> int:
        """Return embedding dimension based on model."""
        return self._config["dimension"]

    @property
    def model(self) -> Any:
        """Get the loaded model, raising if not loaded."""
        if self._model is None:
            # Fallback to global singleton if available
            global _model_instance, _model_name
            if _model_instance is not None and _model_name == self._model_name:
                self._model = _model_instance
            else:
                raise RuntimeError(
                    "Model not loaded. Call initialize() first or use embed() "
                    "which will load it automatically."
                )
        return self._model

    async def initialize(self) -> None:
        """Load the model asynchronously.

        This can be called to pre-warm the model before first use.
        If not called, the model will be loaded automatically on first
        embed() call.
        """
        if self._model is None:
            global _model_instance, _model_name
            if _model_instance is not None and _model_name == self._model_name:
                # Use already-loaded singleton
                self._model = _model_instance
                logger.debug(f"Using existing {self._model_name} model")
            else:
                # Load async
                self._model = await _load_model_async(self._model_name)

    async def _ensure_model_loaded(self) -> None:
        """Ensure model is loaded, loading it async if needed."""
        if self._model is None:
            await self.initialize()

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Loads the model automatically on first call if not already loaded.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        await self._ensure_model_loaded()

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

        Loads the model automatically on first call if not already loaded.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        await self._ensure_model_loaded()

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
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def _embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding (called from thread pool)."""
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
