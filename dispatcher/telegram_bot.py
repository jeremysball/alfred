"""Telegram bot with streaming and typing indicator support."""
import asyncio
import logging
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from dispatcher.dispatcher import Dispatcher

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot that routes to dispatcher with streaming support."""
    
    def __init__(self, token: str, dispatcher: Dispatcher):
        self.token = token
        self.dispatcher = dispatcher
        self.app: Application | None = None
    
    def _get_thread_id(self, update: Update) -> str:
        """Extract thread identifier from update."""
        chat_id = update.effective_chat.id
        
        # Use message_thread_id if in a thread, otherwise use chat_id
        if update.message and update.message.message_thread_id:
            return f"{chat_id}_{update.message.message_thread_id}"
        return str(chat_id)
    
    async def _typing_indicator(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        stop_event: asyncio.Event
    ) -> None:
        """Send typing action every 4 seconds until stop_event is set."""
        while not stop_event.is_set():
            try:
                await context.bot.send_chat_action(
                    chat_id=chat_id,
                    action=ChatAction.TYPING
                )
            except Exception as e:
                logger.warning(f"Failed to send typing indicator: {e}")
            
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=4.0)
            except asyncio.TimeoutError:
                continue
    
    async def _handle_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Route message to dispatcher with streaming and typing indicator."""
        if not update.message or not update.message.text:
            return
        
        thread_id = self._get_thread_id(update)
        chat_id = update.effective_chat.id
        message = update.message.text
        
        logger.info(f"Message in thread {thread_id}: {message[:50]}...")
        
        # Start typing indicator
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(
            self._typing_indicator(context, chat_id, stop_typing)
        )
        
        try:
            # Stream response from dispatcher
            response_text = ""
            
            async for chunk in self.dispatcher.handle_message_streaming(
                chat_id=chat_id,
                thread_id=thread_id,
                message=message
            ):
                response_text = chunk  # Just use the latest chunk (full response)
            
            # Send the complete response
            if response_text:
                await update.message.reply_text(response_text[:4096])
                if len(response_text) > 4096:
                    await update.message.reply_text("... (truncated)")
                logger.info(f"Sent response to thread {thread_id}")
                
        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
        finally:
            # Stop typing indicator
            stop_typing.set()
            await typing_task
    
    async def _handle_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            "🤖 OpenClaw Dispatcher ready.\n\n"
            "Commands:\n"
            "/status — Show active threads\n"
            "/threads — List all threads\n"
            "/kill <thread_id> — Kill a thread's process\n"
            "/cleanup — Kill all processes"
        )
    
    def setup(self) -> Application:
        """Set up the bot application."""
        self.app = Application.builder().token(self.token).build()
        
        # Handlers
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        # Commands are handled by dispatcher via text handler
        self.app.add_handler(
            MessageHandler(filters.COMMAND, self._handle_message)
        )
        
        return self.app
    
    async def run(self) -> None:
        """Run the bot."""
        if not self.app:
            self.setup()
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        logger.info("Telegram bot started")
        
        # Run forever
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
