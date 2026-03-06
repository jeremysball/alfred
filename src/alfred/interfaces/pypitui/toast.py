"""Toast notification system for PyPiTUI CLI.

ToastManager owns toast state and is injected into components that need it.
ToastHandler bridges Python logging to the toast system.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass

# Constants - no magic numbers
TOAST_DURATION_SECONDS = 4  # Auto-dismiss after this time
MAX_VISIBLE_TOASTS = 3  # Maximum toasts on screen


@dataclass
class ToastMessage:
    """A toast notification message.

    Attributes:
        message: The notification text
        level: Severity level (warning, error, info)
        created: Timestamp when created (auto-populated)
    """

    message: str
    level: Literal["warning", "error", "info"]
    created: datetime = field(default_factory=datetime.now)


class ToastManager:
    """Manages toast notification state.

    This class owns the toast list and provides methods to add, get,
    and dismiss toasts. It should be instantiated once and injected
    into components that need toast functionality.
    """

    def __init__(self) -> None:
        """Initialize the toast manager."""
        self._toasts: list[ToastMessage] = []

    def add(self, message: str, level: Literal["warning", "error", "info"]) -> None:
        """Add a toast notification.

        Args:
            message: The notification text to display
            level: Severity level (affects styling)
        """
        toast = ToastMessage(message=message, level=level)
        self._toasts.append(toast)

        # Trim to max visible (keep most recent)
        if len(self._toasts) > MAX_VISIBLE_TOASTS:
            self._toasts = self._toasts[-MAX_VISIBLE_TOASTS:]

    def get_all(self) -> list[ToastMessage]:
        """Get current toast list."""
        return self._toasts

    def dismiss_expired(self) -> None:
        """Remove toasts older than TOAST_DURATION_SECONDS."""
        cutoff = datetime.now() - timedelta(seconds=TOAST_DURATION_SECONDS)
        self._toasts = [t for t in self._toasts if t.created > cutoff]

    def dismiss_all(self) -> None:
        """Clear all toasts."""
        self._toasts = []


class ToastHandler(logging.Handler):
    """Logging handler that creates toasts from log records.

    This is an adapter that bridges Python's logging system to a ToastManager.
    Only captures WARNING+ logs from alfred.* modules to avoid noise.
    """

    def __init__(self, toast_manager: ToastManager) -> None:
        """Initialize the handler with a ToastManager.

        Args:
            toast_manager: The ToastManager to send toast notifications to
        """
        super().__init__(level=logging.WARNING)
        self._toast_manager = toast_manager

    def emit(self, record: logging.LogRecord) -> None:
        """Convert log record to toast if from alfred.* module.

        Args:
            record: The log record to process
        """
        # Only capture src.* modules
        if not record.name.startswith("src."):
            return

        # Map log level to toast level
        level: Literal["warning", "error", "info"]
        if record.levelno >= logging.ERROR:
            level = "error"
        elif record.levelno >= logging.WARNING:
            level = "warning"
        else:
            level = "info"

        # Create toast with formatted message
        message = record.getMessage()
        self._toast_manager.add(message, level)


# Legacy module-level functions for backwards compatibility during migration
# These use a global ToastManager instance
_global_manager: ToastManager | None = None


def _get_global_manager() -> ToastManager:
    """Get or create the global ToastManager (for legacy compatibility)."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ToastManager()
    return _global_manager


def add_toast(message: str, level: Literal["warning", "error", "info"]) -> None:
    """Add a toast notification (legacy module-level function).

    Prefer using a ToastManager instance directly.
    """
    _get_global_manager().add(message, level)


def get_toasts() -> list[ToastMessage]:
    """Get current toast list (legacy module-level function)."""
    return _get_global_manager().get_all()


def dismiss_expired() -> None:
    """Remove expired toasts (legacy module-level function)."""
    _get_global_manager().dismiss_expired()


def dismiss_all() -> None:
    """Clear all toasts (legacy module-level function)."""
    _get_global_manager().dismiss_all()
