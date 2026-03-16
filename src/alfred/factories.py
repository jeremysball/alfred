"""Service factories for Alfred dependency injection.

All service creation is centralized here to support:
- Explicit dependency injection
- Test mocking
- Service locator integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alfred.config import Config

if TYPE_CHECKING:
    from alfred.core import AlfredCore
from alfred.embeddings import create_provider
from alfred.embeddings.provider import EmbeddingProvider
from alfred.llm import LLMFactory, LLMProvider
from alfred.memory import MemoryStore, create_memory_store
from alfred.session import SessionManager
from alfred.storage.sqlite import SQLiteStore
from alfred.tools.search_sessions import SessionSummarizer


class SQLiteStoreFactory:
    """Factory for creating SQLiteStore instances."""

    @staticmethod
    def create(config: Config, embedder: EmbeddingProvider | None = None) -> SQLiteStore:
        """Create SQLiteStore from config.

        Args:
            config: Application configuration with data_dir
            embedder: Optional embedding provider to get dimension from

        Returns:
            Configured SQLiteStore instance
        """
        db_path = config.data_dir / "alfred.db"
        # Get embedding dimension from provider if available
        embedding_dim = embedder.dimension if embedder else 768
        return SQLiteStore(db_path, embedding_dim=embedding_dim)


class EmbeddingProviderFactory:
    """Factory for creating embedding providers."""

    @staticmethod
    def create(config: Config) -> EmbeddingProvider:
        """Create embedding provider from config.

        Args:
            config: Application configuration

        Returns:
            Configured EmbeddingProvider (OpenAI or BGE)
        """
        return create_provider(config)


class LLMProviderFactory:
    """Factory for creating LLM providers."""

    @staticmethod
    def create(config: Config) -> LLMProvider:
        """Create LLM provider from config.

        Args:
            config: Application configuration

        Returns:
            Configured LLMProvider
        """
        return LLMFactory.create(config)


class MemoryStoreFactory:
    """Factory for creating MemoryStore instances."""

    @staticmethod
    def create(config: Config, embedder: EmbeddingProvider) -> MemoryStore:
        """Create MemoryStore from config and embedder.

        Args:
            config: Application configuration
            embedder: Embedding provider for generating vectors

        Returns:
            Configured MemoryStore instance
        """
        return create_memory_store(config, embedder)


class SessionManagerFactory:
    """Factory for creating SessionManager instances."""

    @staticmethod
    def create(store: SQLiteStore, data_dir: Config) -> SessionManager:
        """Create SessionManager from store and config.

        Args:
            store: SQLiteStore for persistence
            data_dir: Data directory for current.json

        Returns:
            Configured SessionManager instance
        """
        return SessionManager(store=store, data_dir=data_dir)

    @classmethod
    def create_from_config(cls, config: Config, embedder: EmbeddingProvider | None = None) -> SessionManager:
        """Create SessionManager from config (creates own SQLiteStore).

        Args:
            config: Application configuration
            embedder: Optional embedding provider for dimension detection

        Returns:
            Configured SessionManager instance
        """
        store = SQLiteStoreFactory.create(config, embedder=embedder)
        return cls.create(store=store, data_dir=config.data_dir)


class SessionSummarizerFactory:
    """Factory for creating SessionSummarizer instances."""

    @staticmethod
    def create(
        store: SQLiteStore,
        llm_client: LLMProvider,
        embedder: EmbeddingProvider,
    ) -> SessionSummarizer:
        """Create SessionSummarizer from dependencies.

        Args:
            store: SQLiteStore for persistence
            llm_client: LLM provider for summary generation
            embedder: Embedding provider for vector search

        Returns:
            Configured SessionSummarizer instance
        """
        return SessionSummarizer(
            llm_client=llm_client,
            embedder=embedder,
            store=store,
        )


class AlfredCoreFactory:
    """Factory for creating fully configured AlfredCore.

    This is the high-level factory that orchestrates all other factories
    to create a complete AlfredCore instance.
    """

    @staticmethod
    def create(config: Config) -> AlfredCore:
        """Create AlfredCore with all services.

        Args:
            config: Application configuration

        Returns:
            Fully configured AlfredCore instance
        """
        from alfred.core import AlfredCore

        return AlfredCore(config)


# Re-export for convenience
__all__ = [
    "AlfredCoreFactory",
    "EmbeddingProviderFactory",
    "LLMProviderFactory",
    "MemoryStoreFactory",
    "SessionManagerFactory",
    "SessionSummarizerFactory",
    "SQLiteStoreFactory",
]
