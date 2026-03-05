"""Unix socket client for cron runner to send notifications.

The cron runner uses this client to communicate with the TUI's socket server.
"""

import asyncio
import contextlib
import logging
from typing import Literal

from src.cron.socket_protocol import SOCKET_NAME, PingMessage, PongMessage, SocketMessage
from src.data_manager import get_cache_dir

logger = logging.getLogger(__name__)


class SocketClient:
    """Unix socket client for sending messages to the TUI.

    Handles connection failures gracefully with buffering and retry logic.
    """

    def __init__(
        self,
        buffer_size: int = 100,
        retry_interval: float = 5.0,
    ):
        """Initialize the socket client.

        Args:
            buffer_size: Maximum messages to buffer when disconnected
            retry_interval: Seconds between connection retry attempts
        """
        self.socket_path = get_cache_dir() / SOCKET_NAME
        self._buffer_size = buffer_size
        self._retry_interval = retry_interval
        self._buffer: list[SocketMessage] = []
        self._writer: asyncio.StreamWriter | None = None
        self._reader: asyncio.StreamReader | None = None
        self._connected = False
        self._connect_task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to the TUI socket server."""
        return self._connected

    async def start(self) -> None:
        """Start the client and begin connection attempts."""
        self._running = True
        self._connect_task = asyncio.create_task(self._connect_loop())
        logger.debug(f"Socket client started, target: {self.socket_path}")

    async def stop(self) -> None:
        """Stop the client and disconnect."""
        self._running = False

        if self._connect_task:
            self._connect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._connect_task
            self._connect_task = None

        await self._disconnect()
        logger.debug("Socket client stopped")

    async def _connect_loop(self) -> None:
        """Background task that maintains connection to TUI."""
        while self._running:
            try:
                if not self._connected:
                    await self._connect()

                if self._connected:
                    # Flush any buffered messages
                    await self._flush_buffer()

                    # Wait a bit before next check
                    await asyncio.sleep(1.0)
                else:
                    # Not connected, wait before retry
                    await asyncio.sleep(self._retry_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection loop error: {e}")
                await self._disconnect()
                await asyncio.sleep(self._retry_interval)

    async def _connect(self) -> None:
        """Attempt to connect to the TUI socket server."""
        if not self.socket_path.exists():
            logger.debug(f"Socket not found: {self.socket_path}")
            return

        try:
            self._reader, self._writer = await asyncio.open_unix_connection(str(self.socket_path))
            self._connected = True
            logger.info(f"Connected to TUI socket: {self.socket_path}")

        except Exception as e:
            logger.debug(f"Failed to connect to socket: {e}")
            self._connected = False

    async def _disconnect(self) -> None:
        """Disconnect from the socket server."""
        self._connected = False

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def _flush_buffer(self) -> None:
        """Send all buffered messages."""
        if not self._connected or not self._writer:
            return

        while self._buffer:
            message = self._buffer.pop(0)
            try:
                self._writer.write(message.to_json().encode("utf-8"))
                await self._writer.drain()
            except Exception as e:
                logger.warning(f"Failed to send buffered message: {e}")
                # Put message back at front of buffer
                self._buffer.insert(0, message)
                await self._disconnect()
                return

    async def send(self, message: SocketMessage) -> bool:
        """Send a message to the TUI.

        If disconnected, the message is buffered and sent when reconnected.

        Args:
            message: The message to send

        Returns:
            True if sent immediately, False if buffered
        """
        if self._connected and self._writer:
            try:
                self._writer.write(message.to_json().encode("utf-8"))
                await self._writer.drain()
                return True
            except Exception as e:
                logger.warning(f"Failed to send message: {e}")
                await self._disconnect()

        # Buffer the message
        self._buffer.append(message)
        if len(self._buffer) > self._buffer_size:
            # Drop oldest message
            dropped = self._buffer.pop(0)
            logger.warning(f"Buffer full, dropped message: {dropped.type}")

        return False

    async def ping(self, timeout: float = 2.0) -> bool:
        """Ping the TUI to check if it's responsive.

        Args:
            timeout: Seconds to wait for pong response

        Returns:
            True if TUI responded with pong
        """
        if not self._connected or not self._writer or not self._reader:
            return False

        try:
            # Send ping
            ping = PingMessage()
            self._writer.write(ping.to_json().encode("utf-8"))
            await self._writer.drain()

            # Wait for pong
            async with asyncio.timeout(timeout):
                line = await self._reader.readline()
                if not line:
                    return False

                response = SocketMessage.from_json(line.decode("utf-8").strip())
                return isinstance(response, PongMessage)

        except Exception as e:
            logger.debug(f"Ping failed: {e}")
            return False

    # Convenience methods for common message types

    async def notify(
        self, message: str, level: Literal["info", "warning", "error"] = "info"
    ) -> bool:
        """Send a toast notification.

        Args:
            message: The notification text
            level: Severity level

        Returns:
            True if sent immediately, False if buffered
        """
        from src.cron.socket_protocol import NotifyMessage

        return await self.send(NotifyMessage(message=message, level=level))
