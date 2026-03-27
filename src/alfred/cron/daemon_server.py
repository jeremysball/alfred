"""Socket server that runs inside the daemon to handle tool requests and push notifications.

The daemon hosts this server, allowing:
- Tools to query/submit/approve/reject jobs via socket
- Interfaces (TUI/WebUI) to receive real-time notifications
"""

import asyncio
import contextlib
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from alfred.cron.scheduler import CronScheduler
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
    SocketMessage,
    SubmitJobRequest,
    SubmitJobResponse,
)
from alfred.data_manager import get_cache_dir

logger = logging.getLogger(__name__)


class DaemonSocketServer:
    """Socket server running inside the daemon.

    Handles requests from tools and pushes notifications to connected clients.
    """

    def __init__(
        self,
        scheduler: CronScheduler,
        on_notify: Callable[[NotifyMessage], None] | None = None,
    ):
        """Initialize the daemon socket server.

        Args:
            scheduler: The cron scheduler for job operations
            on_notify: Optional callback for notifications
        """
        self.socket_path = get_cache_dir() / SOCKET_NAME
        self.scheduler = scheduler
        self._on_notify = on_notify
        self._server: asyncio.Server | None = None
        self._running = False
        self._clients: set[asyncio.StreamWriter] = set()

    @property
    def path(self) -> Path:
        """Get the socket path."""
        return self.socket_path

    async def start(self) -> None:
        """Start the socket server."""
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)

        if self.socket_path.exists():
            logger.debug(f"Removing stale socket file: {self.socket_path}")
            self.socket_path.unlink()

        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
        )
        os.chmod(self.socket_path, 0o600)

        self._running = True
        logger.info(f"Daemon socket server listening on {self.socket_path}")

    async def stop(self) -> None:
        """Stop the socket server."""
        self._running = False

        # Close all client connections
        for writer in list(self._clients):
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
        self._clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        if self.socket_path.exists():
            self.socket_path.unlink()

        logger.info("Daemon socket server stopped")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle a connected client (tool or interface)."""
        peer = writer.get_extra_info("peername") or "unknown"
        logger.debug(f"Client connected: {peer}")
        self._clients.add(writer)

        try:
            while self._running:
                line = await reader.readline()
                if not line:
                    break

                try:
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
            self._clients.discard(writer)
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            logger.debug(f"Client disconnected: {peer}")

    async def _dispatch_message(self, message: SocketMessage, writer: asyncio.StreamWriter) -> None:
        """Dispatch a message to the appropriate handler."""
        try:
            # Handle ping/pong
            if isinstance(message, PingMessage):
                await self._send_response(writer, PongMessage())
                return

            if isinstance(message, PongMessage):
                return

            # Handle notification (from internal daemon -> broadcast to clients)
            if isinstance(message, NotifyMessage):
                if self._on_notify:
                    self._on_notify(message)
                # Broadcast to all other clients
                await self._broadcast(message, exclude=writer)
                return

            # Handle job events (broadcast to all clients)
            if isinstance(message, (JobStartedMessage, JobCompletedMessage, JobFailedMessage)):
                await self._broadcast(message)
                return

            # Handle requests that need responses
            response = await self._handle_request(message)
            if response:
                await self._send_response(writer, response)
                return

            logger.warning(f"Unhandled message type: {type(message).__name__}")

        except Exception as e:
            logger.error(f"Error dispatching message {message.type}: {e}")

    async def _handle_request(self, message: SocketMessage) -> SocketMessage | None:
        """Handle request messages that need responses."""
        if isinstance(message, QueryJobsRequest):
            return await self._handle_query_jobs(message)
        if isinstance(message, SubmitJobRequest):
            return await self._handle_submit_job(message)
        if isinstance(message, ApproveJobRequest):
            return await self._handle_approve_job(message)
        if isinstance(message, RejectJobRequest):
            return await self._handle_reject_job(message)
        return None

    async def _handle_query_jobs(self, request: QueryJobsRequest) -> QueryJobsResponse:
        """Handle job query request."""
        try:
            jobs = await self.scheduler.get_jobs_for_response()
            return QueryJobsResponse(
                request_id=request.request_id,
                jobs=jobs,
            )
        except Exception as e:
            logger.error(f"Failed to query jobs: {e}")
            return QueryJobsResponse(
                request_id=request.request_id,
                jobs=[],
                recent_failures=[{"error": str(e)}],
            )

    async def _handle_submit_job(self, request: SubmitJobRequest) -> SubmitJobResponse:
        """Handle job submission request."""
        try:
            job_id = await self.scheduler.submit_user_job(
                name=request.name,
                expression=request.expression,
                code=request.code,
            )
            return SubmitJobResponse(
                request_id=request.request_id,
                success=True,
                job_id=job_id,
                message=f"Job '{request.name}' submitted successfully",
            )
        except Exception as e:
            return SubmitJobResponse(
                request_id=request.request_id,
                success=False,
                job_id="",
                message=f"Failed to submit job: {e}")

    async def _handle_approve_job(self, request: ApproveJobRequest) -> ApproveJobResponse:
        """Handle job approval request."""
        try:
            result = await self.scheduler.approve_job(request.job_identifier, approved_by="user")
            return ApproveJobResponse(
                request_id=request.request_id,
                success=result.get("success", False),
                job_id=request.job_identifier,
                job_name=result.get("job_name", ""),
                message=result.get("message", ""),
            )
        except Exception as e:
            return ApproveJobResponse(
                request_id=request.request_id,
                success=False,
                job_id=request.job_identifier,
                job_name="",
                message=f"Failed to approve job: {e}")

    async def _handle_reject_job(self, request: RejectJobRequest) -> RejectJobResponse:
        """Handle job rejection request."""
        try:
            # Find and delete the job
            jobs = await self.scheduler._store.load_jobs()
            for job in jobs:
                if job.job_id == request.job_identifier or job.job_id.startswith(request.job_identifier):
                    await self.scheduler._store.delete_job(job.job_id)
                    return RejectJobResponse(
                        request_id=request.request_id,
                        success=True,
                        job_id=job.job_id,
                        message=f"Job '{job.name}' rejected and deleted",
                    )
            return RejectJobResponse(
                request_id=request.request_id,
                success=False,
                job_id=request.job_identifier,
                message=f"Job not found: {request.job_identifier}")
        except Exception as e:
            return RejectJobResponse(
                request_id=request.request_id,
                success=False,
                job_id=request.job_identifier,
                message=f"Failed to reject job: {e}")

    async def _send_response(self, writer: asyncio.StreamWriter, response: SocketMessage) -> None:
        """Send a response to a client."""
        try:
            writer.write(response.to_json().encode("utf-8"))
            await writer.drain()
        except Exception as e:
            logger.debug(f"Failed to send response: {e}")

    async def _broadcast(self, message: SocketMessage, exclude: asyncio.StreamWriter | None = None) -> None:
        """Broadcast a message to all connected clients."""
        dead_clients: set[asyncio.StreamWriter] = set()

        for writer in self._clients:
            if writer is exclude:
                continue
            try:
                writer.write(message.to_json().encode("utf-8"))
                await writer.drain()
            except Exception:
                dead_clients.add(writer)

        # Clean up dead clients
        for writer in dead_clients:
            self._clients.discard(writer)
            writer.close()

    # Public API for the daemon to push notifications

    async def notify_job_started(self, job_id: str, job_name: str) -> None:
        """Broadcast job started notification."""
        await self._broadcast(JobStartedMessage(job_id=job_id, job_name=job_name))

    async def notify_job_completed(self, job_id: str, job_name: str, duration_ms: int, stdout_preview: str = "") -> None:
        """Broadcast job completed notification."""
        await self._broadcast(JobCompletedMessage(
            job_id=job_id,
            job_name=job_name,
            duration_ms=duration_ms,
            stdout_preview=stdout_preview,
        ))

    async def notify_job_failed(self, job_id: str, job_name: str, error: str, duration_ms: int) -> None:
        """Broadcast job failed notification."""
        await self._broadcast(JobFailedMessage(
            job_id=job_id,
            job_name=job_name,
            error=error,
            duration_ms=duration_ms,
        ))

    async def notify(self, message: str, level: Literal["info", "warning", "error"] = "info") -> None:
        """Broadcast a toast notification."""
        await self._broadcast(NotifyMessage(message=message, level=level))
