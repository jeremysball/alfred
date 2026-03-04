"""Async Alfred initialization for faster startup.

Alfred is created with minimal synchronous setup, then heavy
components are initialized in parallel. TUI starts immediately.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from telegram import Bot

from src.agent import Agent
from src.config import Config
from src.context import ContextLoader
from src.cron.notifier import CLINotifier, Notifier, TelegramNotifier
from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore
from src.embeddings import EmbeddingClient
from src.llm import LLMFactory
from src.memory import MemoryStore
from src.search import MemorySearcher
from src.session import SessionManager
from src.session_storage import SessionStorage
from src.token_tracker import TokenTracker
from src.tools import get_registry, register_builtin_tools

logger = logging.getLogger(__name__)


class AlfredAsync:
    """Alfred with async initialization for faster startup.

    Usage:
        alfred = AlfredAsync(config)
        await alfred.initialize()  # Heavy lifting in parallel
    """

    def __init__(self, config: Config, telegram_mode: bool = False) -> None:
        """Minimal synchronous initialization.

        Only stores config and creates lightweight objects.
        Heavy initialization happens in initialize().
        """
        self.config = config
        self._telegram_mode = telegram_mode
        self._data_dir = getattr(config, "data_dir", Path("data"))

        # These will be set in initialize()
        self.llm: Any = None
        self.embedder: Any = None
        self.memory_store: Any = None
        self.searcher: Any = None
        self.context_loader: Any = None
        self.notifier: Notifier | None = None
        self.cron_scheduler: CronScheduler | None = None
        self.tools: Any = None
        self.agent: Agent | None = None
        self.session_manager: SessionManager | None = None
        self.token_tracker = TokenTracker()
        self._last_usage: dict[str, Any] | None = None
        self._telegram_bot: Bot | None = None

    async def initialize(self) -> None:
        """Initialize heavy components in parallel.

        This is where the slow stuff happens:
        - LLM client creation
        - Embedding client creation
        - Memory store loading
        - Cron scheduler loading
        - Session storage loading
        """
        logger.info("Starting Alfred async initialization...")

        # Step 1: Create API clients (independent, can be parallel)
        logger.debug("Creating LLM and embedding clients...")
        self.llm, self.embedder = await asyncio.gather(
            asyncio.to_thread(LLMFactory.create, self.config),
            asyncio.to_thread(EmbeddingClient, self.config),
        )

        # Step 2: Create searcher and context loader
        logger.debug("Creating searcher and context loader...")
        self.searcher = MemorySearcher(min_similarity=0.3)
        self.context_loader = ContextLoader(
            self.config,
            searcher=self.searcher
        )

        # Step 3: Create memory store and session storage (both need embedder)
        logger.debug("Creating memory store and session storage...")
        self.memory_store, session_storage = await asyncio.gather(
            asyncio.to_thread(MemoryStore, self.config, self.embedder),
            asyncio.to_thread(SessionStorage, self.embedder, self._data_dir),
        )
        SessionManager.initialize(session_storage)
        self.session_manager = SessionManager.get_instance()

        # Step 4: Create notifier and cron scheduler (independent)
        logger.debug("Creating notifier and cron scheduler...")
        self.notifier = await self._create_notifier()
        self.cron_scheduler = await asyncio.to_thread(
            CronScheduler,
            store=CronStore(self._data_dir),
            data_dir=self._data_dir,
            notifier=self.notifier,
        )

        # Step 5: Register tools and create agent
        logger.debug("Registering tools and creating agent...")
        register_builtin_tools(
            memory_store=self.memory_store,
            scheduler=self.cron_scheduler,
            config=self.config,
        )
        self.tools = get_registry()
        self.agent = Agent(self.llm, self.tools, max_iterations=-1)

        logger.info("Alfred async initialization complete")

    async def _create_notifier(self) -> Notifier:
        """Create appropriate notifier based on mode."""
        if self._telegram_mode:
            try:
                self._telegram_bot = Bot(token=self.config.telegram_bot_token)
                state_file = self._data_dir / "telegram_state.json"
                chat_id: int | None = None
                if state_file.exists():
                    import json
                    with open(state_file) as f:
                        chat_id = json.load(f).get("chat_id")

                notifier = TelegramNotifier(
                    bot=self._telegram_bot,
                    default_chat_id=chat_id,
                )
                logger.info("TelegramNotifier initialized")
                return notifier
            except Exception as e:
                logger.warning(f"Failed to initialize TelegramNotifier: {e}")

        logger.info("CLINotifier initialized")
        return CLINotifier()

    async def start(self) -> None:
        """Start background services."""
        if self.cron_scheduler:
            try:
                await self.cron_scheduler.start()
                logger.info("Cron scheduler started")
            except Exception as e:
                logger.error(f"Failed to start cron scheduler: {e}")

    async def stop(self) -> None:
        """Stop background services."""
        if self.cron_scheduler:
            try:
                await self.cron_scheduler.stop()
                logger.info("Cron scheduler stopped")
            except Exception as e:
                logger.error(f"Error stopping cron scheduler: {e}")

    @property
    def model_name(self) -> str:
        """Get model name (requires initialization)."""
        if self.llm is None:
            return "initializing..."
        return f"{self.config.default_llm_provider}/{self.config.chat_model}"

    def _on_usage(self, usage: dict[str, Any]) -> None:
        """Callback for LLM usage updates."""
        self.token_tracker.add(usage)
        self._last_usage = usage
