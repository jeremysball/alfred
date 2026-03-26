"""Cron runner entry point.

A standalone process that runs the cron scheduler and executor,
hosting a socket server for tools and interfaces to connect to.

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

from alfred.config import Config, load_config
from alfred.core import AlfredCore
from alfred.cron.daemon import DaemonManager, daemonize
from alfred.cron.daemon_server import DaemonSocketServer
from alfred.cron.scheduler import CronScheduler
from alfred.cron.store import CronStore
from alfred.data_manager import get_cache_dir

logger = logging.getLogger(__name__)


def setup_logging(log_file: Path | None = None, debug: bool = False, daemon_mode: bool = False) -> None:
    """Configure logging for the cron runner.

    Args:
        log_file: Optional file to log to
        debug: Enable debug logging
        daemon_mode: If True, only use StreamHandler since stdout is redirected to log_file
    """
    level = logging.DEBUG if debug else logging.INFO

    handlers: list[logging.Handler] = []

    # Console handler - always needed for foreground mode
    # In daemon mode, stdout is redirected to log_file, so this becomes the file logger
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s"))
    handlers.append(console_handler)

    # File handler - only add in foreground mode (not daemon)
    # In daemon mode, stdout is already redirected to the log file, so adding
    # a FileHandler would cause duplicate log entries
    if log_file and not daemon_mode:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s"))
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers)


async def run_scheduler(
    config: Config,
    daemon_manager: DaemonManager,
    core: AlfredCore,
) -> None:
    """Run the cron scheduler with socket server.

    Args:
        config: Application configuration
        daemon_manager: Daemon manager for signal handling
        core: AlfredCore with registered services for system jobs
    """
    data_dir = config.data_dir
    store = CronStore(data_dir)

    # Create scheduler (socket_server will be set after creation)
    scheduler = CronScheduler(
        store=store,
        data_dir=data_dir,
    )

    # Create socket server for tools and interfaces to connect to
    socket_server = DaemonSocketServer(scheduler=scheduler)

    # Set socket server on scheduler for notifications
    scheduler.set_socket_server(socket_server)

    # Track background tasks to prevent "Task was destroyed but it is pending" warnings
    _background_tasks: set[asyncio.Task[None]] = set()

    # Set up signal handlers
    def _on_shutdown() -> None:
        task = asyncio.create_task(_shutdown(scheduler, socket_server))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    def _on_reload() -> None:
        task = asyncio.create_task(scheduler.reload_jobs())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    daemon_manager.setup_signals(
        on_shutdown=_on_shutdown,
        on_reload=_on_reload,
    )

    # Write PID file
    daemon_manager.write_pid()

    try:
        # Start the socket server
        await socket_server.start()

        # Start the scheduler
        await scheduler.start()

        # Keep running until shutdown
        while not daemon_manager.shutdown_requested:
            # Check for reload requests
            if daemon_manager.reload_requested:
                await scheduler.reload_jobs()

            await asyncio.sleep(1.0)

    finally:
        await _shutdown(scheduler, socket_server)
        daemon_manager.remove_pid()
        logger.info("Cron runner stopped")


async def _shutdown(scheduler: CronScheduler, socket_server: DaemonSocketServer) -> None:
    """Shutdown scheduler and socket server gracefully."""
    await scheduler.stop()
    await socket_server.stop()


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
    setup_logging(log_file=log_file, debug=args.debug, daemon_mode=args.daemon)

    # Daemonize if requested
    if args.daemon:
        print("Starting cron runner as daemon...")
        daemonize(stdout_log=log_file, stderr_log=log_file)
        # After daemonize, we're in the daemon process

    # Load configuration and initialize AlfredCore (registers services in ServiceLocator)
    config = load_config()
    logger.info("Initializing AlfredCore for cron runner...")
    core = AlfredCore(config)

    # Create daemon manager for this process
    daemon_mgr = DaemonManager()

    # Run the scheduler
    try:
        asyncio.run(run_scheduler(config, daemon_mgr, core))
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
