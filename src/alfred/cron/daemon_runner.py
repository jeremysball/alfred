"""AlfredDaemon - Standalone cron daemon for background job processing.

Creates its own AlfredCore with all services (LLM, embedder, memory, etc.).
Configuration is in daemon.toml (separate from main Alfred config).
"""

import asyncio
import logging
import signal

from alfred.core import AlfredCore
from alfred.cron.daemon_config import load_daemon_config, setup_logging

logger = logging.getLogger(__name__)


class AlfredDaemon:
    """Standalone cron daemon (no UI).

    AlfredDaemon runs background jobs using its own AlfredCore.
    It has no user interface - just logs and job execution.

    Configuration is loaded from daemon.toml (not main config).

    Example:
        daemon = AlfredDaemon()
        asyncio.run(daemon.run())
    """

    def __init__(self) -> None:
        """Initialize daemon with AlfredCore services."""
        # Load daemon-specific config
        self.config = load_daemon_config()

        # Setup logging
        setup_logging(self.config)

        # Ensure data directory exists
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

        # Create AlfredCore with daemon config (API keys for LLM/embedder)
        logger.info("Initializing AlfredCore...")
        self.core = AlfredCore(self.config)
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
    daemon = AlfredDaemon()
    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
