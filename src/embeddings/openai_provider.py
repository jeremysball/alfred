"""OpenAI embedding provider.

Wraps the existing OpenAI embedding functionality
behind the EmbeddingProvider interface.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import openai

from src.config import Config
from src.embeddings.provider import EmbeddingProvider

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


def _is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    # Rate limit errors (429)
    if isinstance(error, openai.RateLimitError):
        return True
    # API status errors (503, 504)
    if isinstance(error, openai.APIStatusError):
        return error.status_code in (503, 504, 502, 529)
    # Connection errors
    return isinstance(error, (TimeoutError, ConnectionError))


async def _with_retry[T](
    operation: str,
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> T:
    """Execute async function with exponential backoff retry.

    Retries on transient errors (rate limits, 503s, timeouts).
    Fails fast on permanent errors (auth, bad request, etc.).
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_error = e

            # Don't retry non-transient errors
            if not _is_transient_error(e):
                raise EmbeddingError(f"{operation} failed with non-transient error: {e}", e) from e

            # Last attempt failed
            if attempt == max_retries:
                break

            # Calculate backoff delay: base_delay * 2^attempt, capped at max_delay
            delay = min(base_delay * (2**attempt), max_delay)
            await asyncio.sleep(delay)

    # All retries exhausted
    raise EmbeddingError(
        f"{operation} failed after {max_retries + 1} attempts: {last_error}",
        last_error,
    ) from last_error


class OpenAIProvider(EmbeddingProvider):
    """OpenAI embedding provider.

    Uses OpenAI's text-embedding-3-small model.
    1536-dimensional embeddings.
    """

    def __init__(
        self,
        config: Config,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            config: Application configuration (must have openai_api_key)
            max_retries: Maximum retry attempts for transient errors
            base_delay: Base delay for exponential backoff
        """
        self._client = openai.AsyncOpenAI(api_key=config.openai_api_key)
        self._model = config.embedding_model
        self._max_retries = max_retries
        self._base_delay = base_delay

    @property
    def dimension(self) -> int:
        """Return embedding dimension (1536 for text-embedding-3-small)."""
        return 1536

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """

        async def _embed() -> list[float]:
            response = await self._client.embeddings.create(
                model=self._model,
                input=text,
                encoding_format="float",
            )
            return response.data[0].embedding

        return await _with_retry(
            f"embed({text[:50]}...)",
            _embed,
            max_retries=self._max_retries,
            base_delay=self._base_delay,
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        async def _embed_batch() -> list[list[float]]:
            response = await self._client.embeddings.create(
                model=self._model,
                input=texts,
                encoding_format="float",
            )
            return [item.embedding for item in response.data]

        return await _with_retry(
            f"embed_batch({len(texts)} texts)",
            _embed_batch,
            max_retries=self._max_retries,
            base_delay=self._base_delay,
        )
