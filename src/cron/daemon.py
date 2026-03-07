"""Daemon management for cron runner.

Provides daemonization, PID file management, and signal handling.
"""

import logging
import os
import signal
import sys
from collections.abc import Callable
from pathlib import Path
from types import FrameType

from src.data_manager import get_cache_dir

logger = logging.getLogger(__name__)

# PID file name
PID_FILE = "cron-runner.pid"


class DaemonManager:
    """Manages daemon lifecycle: start, stop, status, PID file.

    Usage:
        daemon = DaemonManager()

        # In daemon process:
        daemon.write_pid()
        daemon.setup_signals(on_shutdown=my_shutdown_handler)

        # To check/control:
        daemon.is_running()
        daemon.stop()
    """

    def __init__(self) -> None:
        """Initialize daemon manager."""
        self.pid_file = get_cache_dir() / PID_FILE
        self._shutdown_requested = False
        self._reload_requested = False

    @property
    def pid(self) -> int:
        """Get current process PID."""
        return os.getpid()

    def read_pid(self) -> int | None:
        """Read PID from file if it exists and process is running.

        Returns:
            PID of running daemon, or None if not running
        """
        if not self.pid_file.exists():
            return None

        try:
            pid_str = self.pid_file.read_text().strip()
            pid = int(pid_str)

            # Check if process is actually running
            if self._is_process_running(pid):
                return pid
            else:
                # Stale PID file, clean it up
                logger.debug(f"Removing stale PID file (process {pid} not running)")
                self.pid_file.unlink()
                return None

        except (ValueError, OSError) as e:
            logger.warning(f"Failed to read PID file: {e}")
            return None

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running."""
        try:
            # Sending signal 0 checks if process exists without actually sending a signal
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def is_running(self) -> bool:
        """Check if the daemon is currently running."""
        return self.read_pid() is not None

    def write_pid(self) -> None:
        """Write current PID to file.

        Should be called by the daemon process after forking.
        """
        # Ensure directory exists
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

        # Write PID
        self.pid_file.write_text(str(self.pid))
        logger.debug(f"Wrote PID {self.pid} to {self.pid_file}")

    def remove_pid(self) -> None:
        """Remove PID file.

        Should be called during graceful shutdown.
        """
        if self.pid_file.exists():
            self.pid_file.unlink()
            logger.debug(f"Removed PID file: {self.pid_file}")

    def stop(self, timeout: float = 10.0) -> bool:
        """Stop the running daemon.

        Sends SIGTERM, then waits for process to exit.
        If it doesn't exit within timeout, sends SIGKILL.

        Args:
            timeout: Seconds to wait for graceful shutdown

        Returns:
            True if daemon was stopped, False if not running
        """
        pid = self.read_pid()
        if not pid:
            logger.info("Daemon is not running")
            return False

        logger.info(f"Stopping daemon (PID {pid})...")

        try:
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit
            import time

            start = time.monotonic()
            while time.monotonic() - start < timeout:
                if not self._is_process_running(pid):
                    logger.info(f"Daemon stopped (PID {pid})")
                    return True
                time.sleep(0.1)

            # Process didn't exit, force kill
            logger.warning(f"Daemon didn't stop gracefully, sending SIGKILL to PID {pid}")
            os.kill(pid, signal.SIGKILL)

            # Wait a bit more
            time.sleep(0.5)
            if not self._is_process_running(pid):
                logger.info(f"Daemon killed (PID {pid})")
                return True
            else:
                logger.error(f"Failed to kill daemon (PID {pid})")
                return False

        except OSError as e:
            logger.error(f"Failed to stop daemon: {e}")
            return False

    def reload(self) -> bool:
        """Send SIGHUP to daemon to trigger job reload.

        Returns:
            True if signal was sent, False if daemon not running
        """
        pid = self.read_pid()
        if not pid:
            logger.info("Daemon is not running")
            return False

        try:
            os.kill(pid, signal.SIGHUP)
            logger.info(f"Sent SIGHUP to daemon (PID {pid})")
            return True
        except OSError as e:
            logger.error(f"Failed to send SIGHUP: {e}")
            return False

    def setup_signals(
        self,
        on_shutdown: Callable[[], None] | None = None,
        on_reload: Callable[[], None] | None = None,
    ) -> None:
        """Set up signal handlers for the daemon.

        Args:
            on_shutdown: Callback for SIGTERM/SIGINT
            on_reload: Callback for SIGHUP
        """

        def handle_shutdown(signum: int, frame: FrameType | None) -> None:
            """Handle shutdown signals (SIGTERM, SIGINT)."""
            sig_name = signal.Signals(signum).name
            logger.info(f"Received {sig_name}, initiating shutdown...")
            self._shutdown_requested = True
            if on_shutdown:
                on_shutdown()

        def handle_reload(signum: int, frame: FrameType | None) -> None:
            """Handle reload signal (SIGHUP)."""
            logger.info("Received SIGHUP, reloading jobs...")
            self._reload_requested = True
            if on_reload:
                on_reload()

        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGHUP, handle_reload)

        logger.debug("Signal handlers configured")

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown was requested via signal."""
        return self._shutdown_requested

    @property
    def reload_requested(self) -> bool:
        """Check if reload was requested via signal."""
        # Auto-clear the flag when checked
        if self._reload_requested:
            self._reload_requested = False
            return True
        return False


def daemonize(
    stdout_log: Path | None = None,
    stderr_log: Path | None = None,
) -> bool:
    """Daemonize the current process using double-fork.

    This function:
    1. Forks and exits parent
    2. Creates new session
    3. Forks again and exits parent
    4. Redirects stdin/stdout/stderr

    Args:
        stdout_log: Path to redirect stdout (default: /dev/null)
        stderr_log: Path to redirect stderr (default: same as stdout)
        ready_file: Path to touch when daemon is ready (optional)

    Returns:
        True in the daemon process, never returns in parent

    Raises:
        OSError: If fork fails
    """
    # First fork
    pid = os.fork()
    if pid > 0:
        # Parent process exits
        sys.exit(0)

    # Create new session and set as process group leader
    os.setsid()

    # Second fork
    pid = os.fork()
    if pid > 0:
        # Parent process exits
        sys.exit(0)

    # Now we're in the daemon process

    # Redirect standard file descriptors
    stdin_path = "/dev/null"
    stdout_path = str(stdout_log) if stdout_log else "/dev/null"
    stderr_path = str(stderr_log) if stderr_log else stdout_path

    # Flush before redirecting
    sys.stdout.flush()
    sys.stderr.flush()

    # Redirect
    with open(stdin_path) as stdin_file:
        os.dup2(stdin_file.fileno(), sys.stdin.fileno())

    with open(stdout_path, "a") as stdout_file:
        os.dup2(stdout_file.fileno(), sys.stdout.fileno())

    with open(stderr_path, "a") as stderr_file:
        os.dup2(stderr_file.fileno(), sys.stderr.fileno())

    logger.debug(f"Daemonized, PID: {os.getpid()}")
    return True
