"""Telegram bot interface for Alfred with streaming support."""

import json
import logging
from pathlib import Path

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
    """Telegram interface with streaming support.

    Manages chat_id persistence for job notifications.
    """

    def __init__(self, config: Config, alfred: Alfred, data_dir: Path | None = None) -> None:
        self.config = config
        self.alfred = alfred
        self.application: Application | None = None

        # Initialize state for chat_id persistence
        self._data_dir = data_dir or Path("data")
        self._state_file = self._data_dir / "telegram_state.json"
        self._chat_id: int | None = None

    @property
    def chat_id(self) -> int | None:
        """Get current chat_id, loading from file if needed."""
        if self._chat_id is None:
            self._load_state()
        return self._chat_id

    def _track_chat_id(self, update: Update) -> None:
        """Track chat_id from incoming message and persist."""
        if update.effective_chat:
            new_chat_id = update.effective_chat.id
            if new_chat_id != self._chat_id:
                self._chat_id = new_chat_id
                self._save_state()

    def _load_state(self) -> None:
        """Load state from file."""
        if self._state_file.exists():
            try:
                with open(self._state_file) as f:
                    data = json.load(f)
                    self._chat_id = data.get("chat_id")
            except Exception as e:
                logger.warning(f"Failed to load telegram state: {e}")

    def _save_state(self) -> None:
        """Save state to file immediately."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_file, "w") as f:
                json.dump({"chat_id": self._chat_id}, f)
        except Exception as e:
            logger.error(f"Failed to save telegram state: {e}")

    def setup(self) -> Application:
        """Initialize telegram application."""
        self.application = Application.builder().token(self.config.telegram_bot_token).build()

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("compact", self.compact))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message))

        return self.application

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.message:
            return

        self._track_chat_id(update)
        await update.message.reply_text("Hello, I'm Alfred. I remember our conversations.")

    async def compact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /compact command."""
        if not update.message:
            return

        self._track_chat_id(update)
        result = await self.alfred.compact()
        await update.message.reply_text(result)

    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages with streaming."""
        if not update.message or not update.message.text:
            return

        self._track_chat_id(update)

        # Send initial message
        response_message = await update.message.reply_text("Thinking...")

        # Stream response
        full_response = ""
        last_update_len = 0
        update_threshold = 50  # Update every 50 chars

        try:
            async for chunk in self.alfred.chat_stream(update.message.text):
                full_response += chunk

                # Update message periodically
                if len(full_response) - last_update_len >= update_threshold:
                    # Truncate if too long for Telegram
                    display_text = full_response[:4000]
                    if len(full_response) > 4000:
                        display_text += "\n[Response too long, truncated...]"

                    await response_message.edit_text(display_text)
                    last_update_len = len(full_response)

            # Final update
            display_text = full_response[:4000]
            if len(full_response) > 4000:
                display_text += "\n[Response too long, truncated...]"

            if display_text != "Thinking...":
                await response_message.edit_text(display_text)

        except Exception as e:
            logger.exception("Error handling message")
            await response_message.edit_text(f"Error: {e}")

    async def run(self) -> None:
        """Run the bot."""
        if not self.application:
            self.setup()

        app = self.application
        assert app is not None, "Application not initialized"
        await app.initialize()
        await app.start()
        updater = app.updater
        if not updater:
            raise RuntimeError("Failed to get Telegram updater")
        await updater.start_polling()

        logger.info("Bot started. Press Ctrl+C to stop.")

        # Keep running until interrupted
        import asyncio

        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        finally:
            await app.stop()
