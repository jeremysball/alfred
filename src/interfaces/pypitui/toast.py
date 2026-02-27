"""Toast notification system for PyPiTUI CLI.

Captures WARNING+ logs from src.* modules and displays them as
toast notifications at the bottom of the screen.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

# Constants - no magic numbers
TOAST_DURATION_SECONDS = 4  # Auto-dismiss after this time
MAX_VISIBLE_TOASTS = 3  # Maximum toasts on screen

# Global toast storage (simple list, could be improved with proper state management)
_toasts: list["ToastMessage"] = []


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


def get_toasts() -> list[ToastMessage]:
    """Get the global toast list (for mutation/testing)."""
    return _toasts


def dismiss_expired() -> None:
    """Remove toasts older than TOAST_DURATION_SECONDS."""
    global _toasts
    cutoff = datetime.now() - timedelta(seconds=TOAST_DURATION_SECONDS)
    _toasts = [t for t in _toasts if t.created > cutoff]


def dismiss_all() -> None:
    """Clear all toasts (called on keypress)."""
    global _toasts
    _toasts = []


def _add_toast(message: str, level: Literal["warning", "error", "info"]) -> None:
    """Add a toast, respecting MAX_VISIBLE_TOASTS limit."""
    global _toasts
    _toasts.append(ToastMessage(message=message, level=level))
    # Trim to max visible (keep most recent)
    if len(_toasts) > MAX_VISIBLE_TOASTS:
        _toasts = _toasts[-MAX_VISIBLE_TOASTS:]


class ToastHandler(logging.Handler):
    """Custom logging handler that routes WARNING+ logs to toasts.

    Only captures logs from src.* modules to avoid noise from
    third-party libraries.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Process a log record and create toast if applicable.

        Args:
            record: The log record to process
        """
        # Only capture src.* modules
        if not record.name.startswith("src."):
            return

        # Only WARNING and above
        if record.levelno < logging.WARNING:
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
        _add_toast(message, level)


def install_toast_handler() -> ToastHandler:
    """Install the toast handler on the root logger with src.* filter.

    Returns:
        The installed handler (for cleanup if needed)
    """
    handler = ToastHandler()
    # Add to root logger to catch all src.* logs
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    return handler
