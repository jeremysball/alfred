"""Notifier interface for sending messages from jobs to users."""

import logging
import sys
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TextIO

logger = logging.getLogger(__name__)


class NotifierError(Exception):
    """Base exception for notifier failures."""
    pass


class Notifier(ABC):
    """Abstract interface for sending notifications to users.

    Implementations handle different delivery channels:
    - TelegramNotifier: Sends via Telegram bot
    - CLINotifier: Outputs to console

    Usage in job code:
        await notify("Hello from my job!")
    """

    @abstractmethod
    async def send(self, message: str) -> None:
        """Send a notification message to the user.

        Args:
            message: The message to send. Plain text, max length depends
                     on implementation (e.g., Telegram has 4096 char limit).

        Returns:
            None

        Raises:
            NotifierError: If delivery fails (implementation-specific)
        """
        pass


class CLINotifier(Notifier):
    """Send notifications to CLI output.

    Outputs formatted messages to stdout or a configurable stream.
    Format: [2026-02-19 10:30:00 JOB NOTIFICATION] Message here
            Continuation lines are indented
    """

    def __init__(self, output_stream: TextIO | None = None) -> None:
        """Initialize CLI notifier.

        Args:
            output_stream: Stream to write to (default: sys.stdout)
        """
        self.output = output_stream or sys.stdout

    async def send(self, message: str) -> None:
        """Send notification to CLI output.

        Args:
            message: Message to display

        Returns:
            None
        """
        try:
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
        except Exception as e:
            # Log error but don't fail the job
            logger.error(f"Failed to send CLI notification: {e}")
