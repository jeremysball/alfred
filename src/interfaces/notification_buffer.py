"""Notification buffer for CLI mode.

Queues notifications while the prompt is active or LLM is streaming,
then displays them after the response completes. Prevents notifications
from clobbering the prompt line.
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class QueuedNotification:
    """A notification waiting to be displayed."""

    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class NotificationBuffer:
    """Buffer for notifications during active CLI states.

    The CLI has two "active" states where notifications shouldn't print directly:
    1. Prompt waiting - user is typing at the prompt
    2. LLM streaming - Rich Live is updating the display

    During these states, notifications are queued. After streaming completes,
    the buffer is flushed and notifications display with a visual separator.

    Thread-safe: Uses collections.deque for atomic append/pop operations.
    """

    def __init__(
        self,
        is_active_callback: Callable[[], bool] | None = None,
    ) -> None:
        """Initialize the notification buffer.

        Args:
            is_active_callback: Optional callback to check if CLI is in active state.
                               If None, uses internal _is_active flag.
        """
        self._buffer: deque[QueuedNotification] = deque()
        self._is_active_flag: bool = False
        self._is_active_callback = is_active_callback

    @property
    def is_active(self) -> bool:
        """Check if CLI is in an active state (prompt or streaming)."""
        if self._is_active_callback:
            return self._is_active_callback()
        return self._is_active_flag

    def set_active(self, active: bool) -> None:
        """Set the active state directly (when not using callback)."""
        self._is_active_flag = active

    def queue(self, message: str) -> None:
        """Queue a notification for later display.

        Args:
            message: The notification message to queue.
        """
        notification = QueuedNotification(message=message)
        self._buffer.append(notification)

    def has_pending(self) -> bool:
        """Check if there are pending notifications."""
        return len(self._buffer) > 0

    def flush(self) -> list[QueuedNotification]:
        """Get all pending notifications and clear the buffer.

        Returns:
            List of queued notifications in order received.
        """
        notifications = list(self._buffer)
        self._buffer.clear()
        return notifications

    def clear(self) -> None:
        """Discard all pending notifications without displaying."""
        self._buffer.clear()

    @property
    def pending_count(self) -> int:
        """Number of notifications waiting to be displayed."""
        return len(self._buffer)
