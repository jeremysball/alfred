"""Verbose logging handler that sends logs to Telegram."""
import logging
import asyncio
from typing import Optional


class TelegramVerboseHandler(logging.Handler):
    """Logging handler that sends verbose logs to Telegram chat."""
    
    def __init__(self, bot_app, chat_id: int):
        super().__init__(level=logging.DEBUG)
        self.bot_app = bot_app
        self.chat_id = chat_id
        self.enabled = False
        self._queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    def emit(self, record: logging.LogRecord) -> None:
        """Send log record to Telegram if verbose mode is enabled."""
        if not self.enabled:
            return
        
        # Only send DEBUG and INFO logs (not WARNING/ERROR which go to normal handlers)
        if record.levelno < logging.DEBUG:
            return
        
        # Format the log message
        msg = self.format(record)
        
        # Truncate if too long
        if len(msg) > 4000:
            msg = msg[:4000] + "..."
        
        # Add to queue (non-blocking)
        try:
            asyncio.create_task(self._send_log(msg))
        except Exception:
            pass  # Don't let logging errors crash the bot
    
    async def _send_log(self, msg: str) -> None:
        """Send log message to Telegram."""
        async with self._lock:
            try:
                await self.bot_app.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"`{msg[:4000]}`",
                    parse_mode="Markdown"
                )
            except Exception as e:
                # If we can't send, just ignore
                pass
    
    def enable(self) -> None:
        """Enable verbose logging to Telegram."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable verbose logging to Telegram."""
        self.enabled = False
    
    def toggle(self) -> bool:
        """Toggle verbose logging. Returns new state."""
        self.enabled = not self.enabled
        return self.enabled


class VerboseLoggerManager:
    """Manages verbose logging for multiple chats."""
    
    def __init__(self):
        self._handlers: dict[int, TelegramVerboseHandler] = {}
    
    def get_handler(self, chat_id: int) -> Optional[TelegramVerboseHandler]:
        """Get handler for a chat."""
        return self._handlers.get(chat_id)
    
    def create_handler(self, chat_id: int, bot_app) -> TelegramVerboseHandler:
        """Create and register a new handler for a chat."""
        handler = TelegramVerboseHandler(bot_app, chat_id)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        self._handlers[chat_id] = handler
        
        # Add to root logger
        logging.getLogger().addHandler(handler)
        
        return handler
    
    def toggle_for_chat(self, chat_id: int, bot_app) -> bool:
        """Toggle verbose logging for a chat. Returns new state."""
        handler = self._handlers.get(chat_id)
        
        if handler is None:
            handler = self.create_handler(chat_id, bot_app)
            handler.enable()
            return True
        
        return handler.toggle()
    
    def is_enabled(self, chat_id: int) -> bool:
        """Check if verbose logging is enabled for a chat."""
        handler = self._handlers.get(chat_id)
        return handler.enabled if handler else False
