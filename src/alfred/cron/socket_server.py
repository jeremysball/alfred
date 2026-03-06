"""Unix socket server for receiving notifications from cron runner.

The TUI runs this server to receive messages from the isolated cron runner process.
"""

import asyncio
import contextlib
import logging
import os
from collections.abc import Callable
from pathlib import Path

from alfred.cron.socket_protocol import (
    SOCKET_NAME,
    JobCompletedMessage,
    JobFailedMessage,
    JobStartedMessage,
    NotifyMessage,
    PingMessage,
    PongMessage,
    RunnerStartedMessage,
    RunnerStoppingMessage,
    SocketMessage,
)
from alfred.data_manager import get_cache_dir

logger = logging.getLogger(__name__)


class SocketServer:
    """Unix socket server that receives messages from the cron runner.

    Runs as a background asyncio task in the TUI process.
    """

    def __init__(
        self,
        on_notify: Callable[[NotifyMessage], None] | None = None,
        on_job_started: Callable[[JobStartedMessage], None] | None = None,
        on_job_completed: Callable[[JobCompletedMessage], None] | None = None,
        on_job_failed: Callable[[JobFailedMessage], None] | None = None,
        on_runner_started: Callable[[RunnerStartedMessage], None] | None = None,
        on_runner_stopping: Callable[[RunnerStoppingMessage], None] | None = None,
    ):
        """Initialize the socket server.

        Args:
            on_notify: Callback for toast notifications
            on_job_started: Callback for job start events
            on_job_completed: Callback for job completion events
            on_job_failed: Callback for job failure events
            on_runner_started: Callback for runner startup events
            on_runner_stopping: Callback for runner shutdown events
        """
        self.socket_path = get_cache_dir() / SOCKET_NAME
        self._server: asyncio.Server | None = None
        self._running = False

        # Callbacks
        self._on_notify = on_notify
        self._on_job_started = on_job_started
        self._on_job_completed = on_job_completed
        self._on_job_failed = on_job_failed
        self._on_runner_started = on_runner_started
        self._on_runner_stopping = on_runner_stopping

    @property
    def path(self) -> Path:
        """Get the socket path."""
        return self.socket_path

    async def start(self) -> None:
        """Start the socket server.

        Creates the socket file and begins listening for connections.
        """
        # Ensure cache directory exists
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove stale socket file if it exists
        if self.socket_path.exists():
            logger.debug(f"Removing stale socket file: {self.socket_path}")
            self.socket_path.unlink()

        # Create the server
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
        )

        # Set socket permissions (allow only owner to read/write)
        os.chmod(self.socket_path, 0o600)

        self._running = True
        logger.info(f"Socket server listening on {self.socket_path}")

    async def stop(self) -> None:
        """Stop the socket server and clean up."""
        self._running = False

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Remove socket file
        if self.socket_path.exists():
            self.socket_path.unlink()
            logger.debug(f"Removed socket file: {self.socket_path}")

        logger.info("Socket server stopped")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a connected client (cron runner).

        Reads messages line-by-line until the client disconnects.
        """
        peer = writer.get_extra_info("peername") or "unknown"
        logger.debug(f"Client connected: {peer}")

        try:
            while self._running:
                # Read a line (message ends with \n)
                line = await reader.readline()
                if not line:
                    # Client disconnected
                    break

                try:
                    # Decode and parse the message
                    data = line.decode("utf-8").strip()
                    if not data:
                        continue

                    message = SocketMessage.from_json(data)
                    await self._dispatch_message(message, writer)

                except Exception as e:
                    logger.warning(f"Failed to parse message: {e}")
                    continue

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            logger.debug(f"Client disconnected: {peer}")

    async def _dispatch_message(self, message: SocketMessage, writer: asyncio.StreamWriter) -> None:
        """Dispatch a message to the appropriate callback."""
        try:
            if isinstance(message, NotifyMessage):
                if self._on_notify:
                    self._on_notify(message)

            elif isinstance(message, JobStartedMessage):
                if self._on_job_started:
                    self._on_job_started(message)

            elif isinstance(message, JobCompletedMessage):
                if self._on_job_completed:
                    self._on_job_completed(message)

            elif isinstance(message, JobFailedMessage):
                if self._on_job_failed:
                    self._on_job_failed(message)

            elif isinstance(message, RunnerStartedMessage):
                if self._on_runner_started:
                    self._on_runner_started(message)

            elif isinstance(message, RunnerStoppingMessage):
                if self._on_runner_stopping:
                    self._on_runner_stopping(message)

            elif isinstance(message, PingMessage):
                # Respond with pong
                pong = PongMessage()
                writer.write(pong.to_json().encode("utf-8"))
                await writer.drain()

            elif isinstance(message, PongMessage):
                # Pong responses are handled by the client
                pass

        except Exception as e:
            logger.error(f"Error dispatching message {message.type}: {e}")
