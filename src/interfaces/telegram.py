"""Telegram bot interface for Alfred."""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.alfred import Alfred
from src.config import Config

logger = logging.getLogger(__name__)


class TelegramInterface:
    """Thin Telegram interface - delegates to Alfred engine."""

    def __init__(self, config: Config, alfred: Alfred) -> None:
        self.config = config
        self.alfred = alfred
        self.application: Application | None = None

    def setup(self) -> Application:
        """Initialize telegram application."""
        self.application = (
            Application.builder()
            .token(self.config.telegram_bot_token)
            .build()
        )

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("compact", self.compact))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.message)
        )

        return self.application

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.message:
            return

        await update.message.reply_text(
            "Hello, I'm Alfred. I remember our conversations."
        )

    async def compact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /compact command."""
        if not update.message:
            return

        result = await self.alfred.compact()
        await update.message.reply_text(result)

    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages - delegate to Alfred."""
        if not update.message or not update.message.text:
            return

        try:
            response = await self.alfred.chat(update.message.text)
            await update.message.reply_text(response.content)
        except Exception as e:
            logger.exception("Error handling message")
            await update.message.reply_text(f"Error: {e}. Please try again.")
            raise  # Fail fast

    async def run(self) -> None:
        """Run the bot."""
        if not self.application:
            self.setup()

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        logger.info("Bot started. Press Ctrl+C to stop.")

        # Keep running until interrupted
        try:
            await self.application.updater.idle()
        finally:
            await self.application.updater.stop()
            await self.application.stop()
