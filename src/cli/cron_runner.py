"""Cron runner entry point.

A standalone process that runs the cron scheduler and executor,
communicating with the TUI via Unix socket.

Usage:
    alfred cron-runner                    # Run in foreground
    alfred cron-runner --daemon           # Run as daemon
    alfred cron-runner --stop             # Stop daemon
    alfred cron-runner --status           # Check daemon status
    alfred cron-runner --reload           # Reload jobs (SIGHUP)
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.config import Config, load_config
from src.cron.daemon import DaemonManager, daemonize
from src.cron.scheduler import CronScheduler
from src.cron.socket_client import SocketClient
from src.cron.store import CronStore
from src.data_manager import get_cache_dir

logger = logging.getLogger(__name__)


def setup_logging(log_file: Path | None = None, debug: bool = False) -> None:
    """Configure logging for the cron runner.

    Args:
        log_file: Optional file to log to
        debug: Enable debug logging
    """
    level = logging.DEBUG if debug else logging.INFO

    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s")
    )
    handlers.append(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers)


async def run_scheduler(
    socket_client: SocketClient,
    config: Config,
    daemon_manager: DaemonManager,
) -> None:
    """Run the cron scheduler with socket client.

    Args:
        socket_client: Socket client for TUI communication
        config: Application configuration
        daemon_manager: Daemon manager for signal handling
    """
    data_dir = config.data_dir
    store = CronStore(data_dir)

    # Create scheduler with socket client for notifications
    scheduler = CronScheduler(
        store=store,
        socket_client=socket_client,
        data_dir=data_dir,
        config=config,
    )

    # Set up signal handlers
    daemon_manager.setup_signals(
        on_shutdown=lambda: asyncio.create_task(scheduler.stop()),
        on_reload=lambda: scheduler.reload_jobs(),
    )

    # Write PID file
    daemon_manager.write_pid()

    # Notify TUI that we've started
    from src.cron.socket_protocol import RunnerStartedMessage

    await socket_client.send(RunnerStartedMessage(pid=daemon_manager.pid))

    try:
        # Start the scheduler
        await scheduler.start()

        # Keep running until shutdown
        while not daemon_manager.shutdown_requested:
            # Check for reload requests
            if daemon_manager.reload_requested:
                scheduler.reload_jobs()

            await asyncio.sleep(1.0)

    finally:
        # Notify TUI that we're stopping
        from src.cron.socket_protocol import RunnerStoppingMessage

        await socket_client.send(RunnerStoppingMessage(reason="shutdown"))

        # Stop scheduler
        await scheduler.stop()

        # Stop socket client
        await socket_client.stop()

        # Clean up PID file
        daemon_manager.remove_pid()

        logger.info("Cron runner stopped")


def main() -> int:
    """Main entry point for cron runner."""
    parser = argparse.ArgumentParser(
        description="Alfred cron runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as a background daemon",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop the running daemon",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check daemon status",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload jobs (send SIGHUP to daemon)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    daemon_manager = DaemonManager()

    # Handle control commands
    if args.stop:
        success = daemon_manager.stop()
        return 0 if success else 1

    if args.status:
        pid = daemon_manager.read_pid()
        if pid:
            print(f"Cron runner is running (PID {pid})")
            return 0
        else:
            print("Cron runner is not running")
            return 1

    if args.reload:
        success = daemon_manager.reload()
        return 0 if success else 1

    # Check if already running
    if daemon_manager.is_running():
        pid = daemon_manager.read_pid()
        print(f"Cron runner is already running (PID {pid})")
        return 1

    # Set up logging
    log_file = get_cache_dir() / "cron-runner.log"
    setup_logging(log_file=log_file, debug=args.debug)

    # Daemonize if requested
    if args.daemon:
        print("Starting cron runner as daemon...")
        daemonize(stdout_log=log_file, stderr_log=log_file)
        # After daemonize, we're in the daemon process

    # Load configuration
    config = load_config()

    # Create components
    socket_client = SocketClient()
    daemon_mgr = DaemonManager()

    # Run the scheduler
    try:
        asyncio.run(run_scheduler(socket_client, config, daemon_mgr))
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
