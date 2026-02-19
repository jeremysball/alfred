"""Notifier interface for sending messages from jobs to users."""

import logging
import sys
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from telegram import Bot

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
    Format: [HH:MM:SS TZ (HH:MM:SS UTC) JOB NOTIFICATION] Message here
            Continuation lines are indented
    """

    def __init__(self, output_stream: TextIO | None = None) -> None:
        """Initialize CLI notifier.

        Args:
            output_stream: Stream to write to (default: sys.stdout)
        """
        self.output = output_stream or sys.stdout

    async def send(self, message: str, chat_id: int | None = None) -> None:
        """Send notification to CLI output immediately.

        Args:
            message: Message to display
            chat_id: Ignored (CLI has no chat routing)

        Returns:
            None
        """
        try:
            # Get local time with timezone and UTC time
            now_local = datetime.now().astimezone()
            now_utc = datetime.now(UTC)

            # Format: "HH:MM:SS TZ (HH:MM:SS UTC)"
            local_str = now_local.strftime("%H:%M:%S") + " " + now_local.strftime("%Z")
            utc_str = now_utc.strftime("%H:%M:%S UTC")
            timestamp = f"{local_str} ({utc_str})"

            lines = message.splitlines() if message else [""]

            for i, line in enumerate(lines):
                if i == 0:
                    formatted = f"[{timestamp} JOB NOTIFICATION] {line}\n"
                else:
                    # Indent continuation lines to align with first line
                    # Length of "[{timestamp} JOB NOTIFICATION] "
                    prefix_len = len(timestamp) + 22
                    formatted = f"{' ' * prefix_len}{line}\n"
                self.output.write(formatted)

            self.output.flush()
        except Exception as e:
            # Log error but don't fail the job
            logger.error(f"Failed to send CLI notification: {e}")


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
