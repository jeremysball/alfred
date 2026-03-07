"""Factories for creating tool dependencies."""

from alfred.embeddings.provider import EmbeddingProvider
from alfred.llm import LLMProvider
from alfred.storage.sqlite import SQLiteStore
from alfred.tools.search_sessions import SessionSummarizer


class SummarizerFactory:
    """Factory for creating SessionSummarizer with dependencies."""

    def __init__(
        self,
        store: SQLiteStore,
        llm_client: LLMProvider,
        embedder: EmbeddingProvider,
    ) -> None:
        self.store = store
        self.llm_client = llm_client
        self.embedder = embedder

    def create(self) -> SessionSummarizer:
        """Create configured SessionSummarizer."""
        return SessionSummarizer(
            llm_client=self.llm_client,
            embedder=self.embedder,
            store=self.store,
        )
