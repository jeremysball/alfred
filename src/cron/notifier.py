"""Notifier interface for sending messages from jobs to users."""

from abc import ABC, abstractmethod


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
