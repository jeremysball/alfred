"""Unix socket server for receiving notifications from cron runner.

The TUI runs this server to receive messages from the isolated cron runner process.
"""

import asyncio
import contextlib
import inspect
import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

from alfred.cron.socket_protocol import (
    SOCKET_NAME,
    ApproveJobRequest,
    ApproveJobResponse,
    JobCompletedMessage,
    JobFailedMessage,
    JobStartedMessage,
    NotifyMessage,
    PingMessage,
    PongMessage,
    QueryJobsRequest,
    QueryJobsResponse,
    RejectJobRequest,
    RejectJobResponse,
    RunnerStartedMessage,
    RunnerStoppingMessage,
    SocketMessage,
    SubmitJobRequest,
    SubmitJobResponse,
)
from alfred.data_manager import get_cache_dir

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


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
        on_query_jobs: Callable[[QueryJobsRequest], QueryJobsResponse | Awaitable[QueryJobsResponse]] | None = None,
        on_submit_job: Callable[[SubmitJobRequest], SubmitJobResponse | Awaitable[SubmitJobResponse]] | None = None,
        on_approve_job: Callable[[ApproveJobRequest], ApproveJobResponse | Awaitable[ApproveJobResponse]] | None = None,
        on_reject_job: Callable[[RejectJobRequest], RejectJobResponse | Awaitable[RejectJobResponse]] | None = None,
    ):
        """Initialize the socket server.

        Args:
            on_notify: Callback for toast notifications
            on_job_started: Callback for job start events
            on_job_completed: Callback for job completion events
            on_job_failed: Callback for job failure events
            on_runner_started: Callback for runner startup events
            on_runner_stopping: Callback for runner shutdown events
            on_query_jobs: Callback for job status queries
            on_submit_job: Callback for job submission requests
            on_approve_job: Callback for job approval requests
            on_reject_job: Callback for job rejection requests
        """
        self.socket_path = get_cache_dir() / SOCKET_NAME
        self._server: asyncio.Server | None = None
        self._running = False

        # Callbacks
        self._on_notify: Callable[[NotifyMessage], None] | None = on_notify
        self._on_job_started: Callable[[JobStartedMessage], None] | None = on_job_started
        self._on_job_completed: Callable[[JobCompletedMessage], None] | None = on_job_completed
        self._on_job_failed: Callable[[JobFailedMessage], None] | None = on_job_failed
        self._on_runner_started: Callable[[RunnerStartedMessage], None] | None = on_runner_started
        self._on_runner_stopping: Callable[[RunnerStoppingMessage], None] | None = on_runner_stopping
        self._on_query_jobs: Callable[[QueryJobsRequest], QueryJobsResponse | Awaitable[QueryJobsResponse]] | None = on_query_jobs
        self._on_submit_job: Callable[[SubmitJobRequest], SubmitJobResponse | Awaitable[SubmitJobResponse]] | None = on_submit_job
        self._on_approve_job: Callable[[ApproveJobRequest], ApproveJobResponse | Awaitable[ApproveJobResponse]] | None = on_approve_job
        self._on_reject_job: Callable[[RejectJobRequest], RejectJobResponse | Awaitable[RejectJobResponse]] | None = on_reject_job

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

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
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

    def _get_handler(self, message: SocketMessage) -> Callable[[Any], None] | None:
        """Get the appropriate handler callback for a message type."""
        if isinstance(message, NotifyMessage):
            return self._on_notify
        if isinstance(message, JobStartedMessage):
            return self._on_job_started
        if isinstance(message, JobCompletedMessage):
            return self._on_job_completed
        if isinstance(message, JobFailedMessage):
            return self._on_job_failed
        if isinstance(message, RunnerStartedMessage):
            return self._on_runner_started
        if isinstance(message, RunnerStoppingMessage):
            return self._on_runner_stopping
        return None

    def _get_request_handler(self, message: SocketMessage) -> Callable[[Any], SocketMessage | Awaitable[SocketMessage]] | None:
        """Get the appropriate handler for request messages that need responses."""
        if isinstance(message, QueryJobsRequest):
            return self._on_query_jobs
        if isinstance(message, SubmitJobRequest):
            return self._on_submit_job
        if isinstance(message, ApproveJobRequest):
            return self._on_approve_job
        if isinstance(message, RejectJobRequest):
            return self._on_reject_job
        return None

    async def _send_response(self, writer: asyncio.StreamWriter, response: SocketMessage) -> None:
        """Send a response message back to the client."""
        writer.write(response.to_json().encode("utf-8"))
        await writer.drain()

    @staticmethod
    async def _resolve_response(
        raw: SocketMessage | Awaitable[SocketMessage],
    ) -> SocketMessage:
        """Resolve a response that may be sync or async."""
        if inspect.isawaitable(raw):
            return await raw
        return raw

    async def _dispatch_message(self, message: SocketMessage, writer: asyncio.StreamWriter) -> None:
        """Dispatch a message to the appropriate callback."""
        try:
            # Handle ping/pong directly
            if isinstance(message, PingMessage):
                await self._send_response(writer, PongMessage())
                return

            if isinstance(message, PongMessage):
                # Pong responses are handled by the client
                return

            # Handle simple event messages
            handler = self._get_handler(message)
            if handler:
                handler(message)
                return

            # Handle request/response messages
            request_handler = self._get_request_handler(message)
            if request_handler:
                raw_response: SocketMessage | Awaitable[SocketMessage] = request_handler(message)
                response = await self._resolve_response(raw_response)
                await self._send_response(writer, response)
                return

            logger.warning(f"Unhandled message type: {type(message).__name__}")

        except Exception as e:
            logger.error(f"Error dispatching message {message.type}: {e}")
