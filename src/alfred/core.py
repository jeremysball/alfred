"""AlfredCore - Shared services container for Alfred and CronDaemon.

Provides centralized initialization and management of core services
shared between the CLI/Telegram interface and the standalone cron daemon.
"""

import logging

from alfred.config import Config
from alfred.container import ServiceLocator
from alfred.cron.scheduler import CronScheduler
from alfred.cron.store import CronStore
from alfred.embeddings.provider import EmbeddingProvider
from alfred.factories import (
    EmbeddingProviderFactory,
    LLMProviderFactory,
    MemoryStoreFactory,
    SessionManagerFactory,
    SessionSummarizerFactory,
    SQLiteStoreFactory,
)
from alfred.llm import LLMProvider
from alfred.session import SessionManager
from alfred.storage.sqlite import SQLiteStore
from alfred.tools.search_sessions import SessionSummarizer

logger = logging.getLogger(__name__)


class AlfredCore:
    """Core Alfred services shared between CLI, Telegram, and daemon.

    AlfredCore initializes and manages all shared services:
    - SQLiteStore for unified storage
    - EmbeddingProvider for vector operations
    - LLMProvider for language model access
    - MemoryStore for semantic memory
    - SessionManager for conversation management
    - SessionSummarizer for session summaries

    Services are registered in ServiceLocator for global access by
    cron jobs and other components that cannot use constructor injection.

    Example:
        config = load_config()
        core = AlfredCore(config)

        # Access services directly
        llm = core.llm
        store = core.sqlite_store

        # Or via ServiceLocator from anywhere
        summarizer = ServiceLocator.resolve(SessionSummarizer)
    """

    def __init__(self, config: Config) -> None:
        """Initialize all shared services.

        Args:
            config: Application configuration

        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config

        # Ensure data directory exists
        config.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize services via factories
        self._init_services()
        self._register_in_locator()

        logger.info("AlfredCore initialized")

    def _init_services(self) -> None:
        """Initialize all shared services via factories."""
        logger.debug("Initializing embedder...")
        self.embedder = EmbeddingProviderFactory.create(self.config)

        logger.debug("Initializing SQLite store...")
        self.sqlite_store = SQLiteStoreFactory.create(self.config, embedder=self.embedder)

        logger.debug("Initializing LLM...")
        self.llm = LLMProviderFactory.create(self.config)

        logger.debug("Initializing memory store...")
        self.memory_store = MemoryStoreFactory.create(self.config, self.embedder)

        logger.debug("Initializing session manager...")
        self.session_manager = SessionManagerFactory.create(
            store=self.sqlite_store,
            data_dir=self.config.data_dir,
        )

        logger.debug("Initializing summarizer...")
        self.summarizer = SessionSummarizerFactory.create(
            store=self.sqlite_store,
            llm_client=self.llm,
            embedder=self.embedder,
        )

    def _register_in_locator(self) -> None:
        """Register services in ServiceLocator for global access.

        This allows cron jobs and other components to resolve dependencies
        without explicit constructor injection.
        """
        logger.debug("Registering services in ServiceLocator...")

        ServiceLocator.register(SQLiteStore, self.sqlite_store)
        ServiceLocator.register(EmbeddingProvider, self.embedder)
        ServiceLocator.register(LLMProvider, self.llm)
        ServiceLocator.register(SessionManager, self.session_manager)
        ServiceLocator.register(SessionSummarizer, self.summarizer)

    @property
    def cron_scheduler(self) -> CronScheduler:
        """Get configured cron scheduler.

        Returns:
            CronScheduler configured with this core's data directory
        """
        return CronScheduler(
            store=CronStore(self.config.data_dir),
            data_dir=self.config.data_dir,
        )
