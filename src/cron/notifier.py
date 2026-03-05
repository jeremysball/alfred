"""Notifier interface for sending messages from jobs to users."""

import logging
import sys
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, Protocol, TextIO, runtime_checkable

if TYPE_CHECKING:
    from telegram import Bot

    from src.interfaces.notification_buffer import NotificationBuffer

logger = logging.getLogger(__name__)


class NotifierError(Exception):
    """Base exception for notifier failures."""

    pass


@runtime_checkable
class ToastManagerProtocol(Protocol):
    """Protocol for ToastManager to avoid circular imports."""

    def add(self, message: str, level: Literal["warning", "error", "info"]) -> None:
        """Add a toast notification."""
        ...

    def get_all(self) -> list[Any]:
        """Get all active toasts."""
        ...

    def dismiss_all(self) -> None:
        """Dismiss all toasts."""
        ...


class Notifier(ABC):
    """Abstract interface for sending notifications to users.

    Implementations handle different delivery channels:
    - TelegramNotifier: Sends via Telegram bot
    - CLINotifier: Outputs to console

    Usage in job code:
        await notify("Hello from my job!")
    """

    @abstractmethod
    async def send(self, message: str, chat_id: int | None = None) -> None:
        """Send a notification message to the user.

        Args:
            message: The message to send. Plain text, max length depends
                     on implementation (e.g., Telegram has 4096 char limit).
            chat_id: Optional chat_id for per-job routing (TelegramNotifier only).

        Returns:
            None

        Raises:
            NotifierError: If delivery fails (implementation-specific)
        """
        pass


class CLINotifier(Notifier):
    """Send notifications to CLI output.

    Outputs formatted messages to stdout or a configurable stream.
    When a NotificationBuffer is set and active, notifications are queued
    instead of printed immediately. This prevents notifications from
    clobbering the prompt line during user input or LLM streaming.

    In TUI mode (toast_manager provided), notifications appear as toast
    overlays instead of inline text.

    Format: [2026-02-19 10:30:00 JOB NOTIFICATION] Message here
            Continuation lines are indented
    """

    def __init__(
        self,
        output_stream: TextIO | None = None,
        buffer: "NotificationBuffer | None" = None,
        toast_manager: ToastManagerProtocol | None = None,
    ) -> None:
        """Initialize CLI notifier.

        Args:
            output_stream: Stream to write to (default: sys.stdout)
            buffer: Optional notification buffer for queuing during active states
            toast_manager: Optional ToastManager for TUI toast notifications
        """
        self.output = output_stream or sys.stdout
        self.buffer = buffer
        self._toast_manager = toast_manager

    def set_buffer(self, buffer: "NotificationBuffer | None") -> None:
        """Set or clear the notification buffer.

        Args:
            buffer: The buffer to use, or None to disable buffering.
        """
        self.buffer = buffer

    def set_toast_manager(self, toast_manager: ToastManagerProtocol | None) -> None:
        """Set or clear the toast manager.

        Args:
            toast_manager: The ToastManager to use, or None to disable toasts.
        """
        self._toast_manager = toast_manager

    async def send(self, message: str, chat_id: int | None = None) -> None:
        """Send notification to CLI output.

        If buffer is active, queues the notification for later display.
        If toast_manager is set, sends as toast overlay.
        Otherwise, displays immediately.

        Args:
            message: Message to display
            chat_id: Ignored (CLI has no chat routing)

        Returns:
            None
        """
        try:
            # In TUI mode, send as toast
            # ToastManager automatically defers toasts when stdout is captured
            # (e.g., during cron job execution) and shows them once freed.
            if self._toast_manager is not None:
                self._toast_manager.add(message, "info")
                logger.debug(f"Sent toast notification: {message[:50]}...")
                return

            # Queue if buffer exists and is active
            if self.buffer and self.buffer.is_active:
                self.buffer.queue(message)
                logger.debug(f"Queued notification (buffer active): {message[:50]}...")
                return

            # Display immediately
            self._display(message)
        except Exception as e:
            # Log error but don't fail the job
            logger.error(f"Failed to send CLI notification: {e}")

    def _display(self, message: str) -> None:
        """Display a notification immediately to output stream.

        Args:
            message: The message to display.
        """
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        lines = message.splitlines() if message else [""]

        for i, line in enumerate(lines):
            if i == 0:
                formatted = f"[{timestamp} JOB NOTIFICATION] {line}\n"
            else:
                # Indent continuation lines to align with first line
                formatted = f"{' ' * 32}{line}\n"
            self.output.write(formatted)

        self.output.flush()

    def flush_buffer(self) -> None:
        """Flush all pending notifications from buffer.

        Displays queued notifications with a visual separator.
        Called by CLI after LLM response completes.
        """
        if not self.buffer or not self.buffer.has_pending():
            return

        notifications = self.buffer.flush()
        count = len(notifications)

        # Visual separator
        self.output.write(f"\n{'─' * 20} Jobs ({count}) {'─' * 20}\n")

        for notification in notifications:
            self._display(notification.message)

        self.output.write(f"{'─' * 52}\n\n")
        self.output.flush()


class TelegramNotifier(Notifier):
    """Send notifications via Telegram bot.

    Uses an existing Bot instance from TelegramInterface to avoid
    duplicate connections. Supports per-job chat_id routing with
    a default fallback.
    """

    # Telegram message length limit
    MAX_MESSAGE_LENGTH = 4096
    TRUNCATE_LENGTH = 4093  # Leave room for "..."

    def __init__(self, bot: "Bot", default_chat_id: int | None = None) -> None:
        """Initialize Telegram notifier.

        Args:
            bot: Telegram Bot instance (from TelegramInterface)
            default_chat_id: Default chat to send to if job has no chat_id
        """
        self.bot = bot
        self.default_chat_id = default_chat_id

    async def send(self, message: str, chat_id: int | None = None) -> None:
        """Send notification via Telegram.

        Args:
            message: Message to send (truncated to 4096 chars if needed)
            chat_id: Target chat, falls back to default_chat_id if None

        Returns:
            None
        """
        target = chat_id or self.default_chat_id
        if target is None:
            logger.warning("No chat_id available for Telegram notification")
            return

        # Truncate if needed (Telegram limit is 4096 chars)
        if len(message) > self.MAX_MESSAGE_LENGTH:
            message = message[: self.TRUNCATE_LENGTH] + "..."

        try:
            await self.bot.send_message(chat_id=target, text=message)
        except Exception as e:
            # Log error but don't fail the job
            logger.error(f"Failed to send Telegram notification: {e}")
