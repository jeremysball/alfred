"""AlfredDaemon - Standalone cron daemon for background job processing.

Runs independently of Alfred CLI/Telegram, creating its own AlfredCore
with all necessary services (LLM, embedder, memory store, etc.).
"""

import asyncio
import logging
import signal

from alfred.config import Config, load_config
from alfred.core import AlfredCore

logger = logging.getLogger(__name__)


class AlfredDaemon:
    """Standalone cron daemon (no UI).

    AlfredDaemon runs background jobs using shared services from AlfredCore.
    It has no user interface - just logs and job execution.

    Example:
        config = load_config()
        daemon = AlfredDaemon(config)
        asyncio.run(daemon.run())
    """

    def __init__(self, config: Config) -> None:
        """Initialize daemon with AlfredCore services.

        Args:
            config: Application configuration
        """
        self.config = config

        # Ensure data directory exists
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

        # Create AlfredCore with all services (LLM, embedder, memory, etc.)
        logger.info("Initializing AlfredCore...")
        self.core = AlfredCore(config)
        logger.info("AlfredCore initialized")

        # Shutdown event (created in run when event loop exists)
        self._shutdown_event: asyncio.Event | None = None

    def _setup_signal_handlers(self) -> None:
        """Setup handlers for graceful shutdown on SIGINT/SIGTERM."""
        loop = asyncio.get_running_loop()

        def signal_handler() -> None:
            logger.info("Shutdown signal received, stopping daemon...")
            if self._shutdown_event:
                self._shutdown_event.set()

        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)

    async def run(self) -> None:
        """Start the daemon and run until shutdown signal.

        Starts the cron scheduler and waits for shutdown signal.
        """
        logger.info("Starting AlfredDaemon...")

        # Create shutdown event and setup signal handlers
        self._shutdown_event = asyncio.Event()
        self._setup_signal_handlers()

        # Start the cron scheduler
        await self.core.cron_scheduler.start()
        logger.info("Cron scheduler started")

        # Keep running until shutdown signal
        logger.info("AlfredDaemon running (press Ctrl+C to stop)")
        await self._shutdown_event.wait()

        # Graceful shutdown
        logger.info("Shutting down AlfredDaemon...")
        await self.core.cron_scheduler.stop()
        logger.info("AlfredDaemon stopped")


def main() -> None:
    """Entry point for CLI: `alfred cron daemon`."""
    # Load config first to get log level
    config = load_config()

    # Setup logging with config level (default INFO)
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Start daemon
    daemon = AlfredDaemon(config)
    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
