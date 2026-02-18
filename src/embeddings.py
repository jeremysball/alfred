"""OpenAI embedding client for semantic memory retrieval."""

import math
from collections.abc import Awaitable, Callable
from typing import TypeVar

import openai

from src.config import Config


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


T = TypeVar("T")


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
    import asyncio

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


class EmbeddingClient:
    """Client for generating text embeddings via OpenAI API."""

    def __init__(
        self,
        config: Config,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        self.client = openai.AsyncOpenAI(api_key=config.openai_api_key)
        self.model = config.embedding_model
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Retries on transient errors (rate limits, 503s).
        Fails fast on permanent errors (auth, bad request).
        """

        async def _embed() -> list[float]:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float",
            )
            return response.data[0].embedding

        return await _with_retry(
            f"embed({text[:50]}...)",
            _embed,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Retries on transient errors (rate limits, 503s).
        Fails fast on permanent errors (auth, bad request).
        """
        if not texts:
            return []

        async def _embed_batch() -> list[list[float]]:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float",
            )
            return [item.embedding for item in response.data]

        return await _with_retry(
            f"embed_batch({len(texts)} texts)",
            _embed_batch,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
        )


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))  # noqa: B905
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
