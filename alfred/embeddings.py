"""OpenAI embeddings for semantic memory search."""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """Base class for embedding providers."""

    async def embed(self, text: str) -> list[float]:
        """Embed text into vector."""
        raise NotImplementedError

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider using text-embedding-3-small."""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
        self._client = None

        if api_key:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=api_key)
            except ImportError:
                logger.error("openai package not installed")
                raise

    async def embed(self, text: str) -> list[float]:
        """Embed single text."""
        if not self._client:
            raise RuntimeError("OpenAI client not initialized - no API key")

        try:
            response = await self._client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        if not self._client:
            raise RuntimeError("OpenAI client not initialized - no API key")

        try:
            response = await self._client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [d.embedding for d in response.data]
        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}")
            raise


class SimpleEmbeddingProvider(EmbeddingProvider):
    """Simple fallback using sentence-transformers (local)."""

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        self.model_name = model
        self._model = None

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model)
        except ImportError:
            logger.warning("sentence-transformers not installed, using random embeddings")
            self._model = None

    async def embed(self, text: str) -> list[float]:
        """Embed text locally."""
        if self._model:
            import asyncio
            # Run in thread pool since sentence-transformers is sync
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, lambda: self._model.encode(text).tolist()
            )
            return embedding
        else:
            # Fallback: random embedding for testing
            import random
            random.seed(hash(text))
            return [random.random() for _ in range(384)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed batch locally."""
        if self._model:
            import asyncio
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, lambda: self._model.encode(texts).tolist()
            )
            return embeddings
        else:
            return [await self.embed(t) for t in texts]


class MemoryRetriever:
    """Semantic memory retrieval using embeddings."""

    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider
        self._documents: list[str] = []
        self._embeddings: list[list[float]] = []
        self._metadata: list[dict] = []

    async def add_document(self, text: str, metadata: Optional[dict] = None) -> None:
        """Add document to retrieval index."""
        embedding = await self.provider.embed(text)
        self._documents.append(text)
        self._embeddings.append(embedding)
        self._metadata.append(metadata or {})
        logger.debug(f"Added document: {text[:50]}...")

    async def add_documents(self, texts: list[str], metadatas: Optional[list[dict]] = None) -> None:
        """Add multiple documents."""
        embeddings = await self.provider.embed_batch(texts)
        self._documents.extend(texts)
        self._embeddings.extend(embeddings)
        if metadatas:
            self._metadata.extend(metadatas)
        else:
            self._metadata.extend([{} for _ in texts])
        logger.info(f"Added {len(texts)} documents")

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)
        if a_norm == 0 or b_norm == 0:
            return 0.0
        return float(np.dot(a, b) / (a_norm * b_norm))

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search for most similar documents."""
        if not self._documents:
            return []

        query_embedding = await self.provider.embed(query)

        # Calculate similarities
        similarities = [
            (i, self._cosine_similarity(query_embedding, doc_emb))
            for i, doc_emb in enumerate(self._embeddings)
        ]

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top k
        results = []
        for idx, score in similarities[:top_k]:
            results.append({
                "text": self._documents[idx],
                "score": score,
                "metadata": self._metadata[idx]
            })

        return results

    def clear(self) -> None:
        """Clear all documents."""
        self._documents.clear()
        self._embeddings.clear()
        self._metadata.clear()
        logger.info("Cleared all documents")
