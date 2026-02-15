"""Telegram bot with commands and persistent Pi processes per thread."""
import asyncio
import logging
import time
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from openclaw_pi.dispatcher import Dispatcher
from openclaw_pi.verbose_logger import VerboseLoggerManager

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot with persistent Pi processes per thread."""
    
    def __init__(self, token: str, dispatcher: Dispatcher):
        self.token = token
        self.dispatcher = dispatcher
        self.app: Application | None = None
        self.verbose_manager = VerboseLoggerManager()
    
    def _get_thread_id(self, update: Update) -> str:
        """Extract thread identifier from update."""
        chat_id = update.effective_chat.id
        
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
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            "🤖 OpenClaw Pi\n\n"
            "Persistent Pi agent per thread.\n"
            "Each thread gets its own long-running Pi process.\n\n"
            "Commands:\n"
            "/status — Active and stored threads\n"
            "/threads — List threads\n"
            "/kill <id> — Kill thread process\n"
            "/cleanup — Kill all processes\n"
            "/tokens — Token usage stats\n"
            "/compact [prompt] — Compact memories with optional LLM prompt\n"
            "/verbose — Toggle verbose logging to chat\n"
            "/subagent <task> — Spawn background sub-agent"
        )
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        response = await self.dispatcher.handle_command(
            self._get_thread_id(update),
            "/status"
        )
        await update.message.reply_text(response)
    
    async def _handle_threads(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /threads command."""
        response = await self.dispatcher.handle_command(
            self._get_thread_id(update),
            "/threads"
        )
        await update.message.reply_text(response)
    
    async def _handle_kill(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /kill command."""
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /kill <thread_id>")
            return
        
        response = await self.dispatcher.handle_command(
            self._get_thread_id(update),
            f"/kill {args[0]}"
        )
        await update.message.reply_text(response)
    
    async def _handle_cleanup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cleanup command."""
        response = await self.dispatcher.handle_command(
            self._get_thread_id(update),
            "/cleanup"
        )
        await update.message.reply_text(response)

    async def _handle_tokens(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /tokens command."""
        response = await self.dispatcher.handle_command(
            self._get_thread_id(update),
            "/tokens"
        )
        await update.message.reply_text(response)

    async def _handle_compact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /compact command."""
        args = context.args
        prompt = " ".join(args) if args else ""
        
        response = await self.dispatcher.handle_command(
            self._get_thread_id(update),
            f"/compact {prompt}"
        )
        await update.message.reply_text(response)

    async def _handle_verbose(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /verbose command to toggle verbose logging."""
        if not self.app:
            await update.message.reply_text("❌ Bot not initialized")
            return
        
        chat_id = update.effective_chat.id
        enabled = self.verbose_manager.toggle_for_chat(chat_id, self.app)
        
        if enabled:
            await update.message.reply_text(
                "🔊 Verbose logging enabled\n\n"
                "Debug logs will now be sent to this chat.\n"
                "Use /verbose again to disable."
            )
        else:
            await update.message.reply_text(
                "🔇 Verbose logging disabled\n\n"
                "Debug logs will no longer be sent to this chat."
            )

    async def _handle_subagent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /subagent command."""
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /subagent <task description>")
            return
        
        task = " ".join(args)
        thread_id = self._get_thread_id(update)
        chat_id = update.effective_chat.id
        
        await update.message.reply_text(f"🔄 Spawning sub-agent: {task[:50]}...")
        
        response = await self.dispatcher.spawn_subagent(
            chat_id=chat_id,
            thread_id=thread_id,
            task=task
        )
        await update.message.reply_text(response)
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route message to dispatcher with typing indicator."""
        if not update.message or not update.message.text:
            return
        
        start_time = time.time()
        thread_id = self._get_thread_id(update)
        chat_id = update.effective_chat.id
        message = update.message.text
        
        logger.info(f"[TG] Message received thread={thread_id}, len={len(message)}")
        
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(
            self._typing_indicator(context, chat_id, stop_typing)
        )
        
        try:
            t0 = time.time()
            response = await self.dispatcher.handle_message(
                chat_id=chat_id,
                thread_id=thread_id,
                message=message
            )
            dispatch_time = time.time() - t0
            logger.info(f"[TG] Dispatcher returned in {dispatch_time:.2f}s")
            
            if response:
                t0 = time.time()
                await update.message.reply_text(response[:4096])
                send_time = time.time() - t0
                logger.info(f"[TG] Reply sent in {send_time:.2f}s")
                
                if len(response) > 4096:
                    await update.message.reply_text("... (truncated)")
            else:
                logger.warning(f"[TG] Empty response for thread={thread_id}")
                    
        except Exception as e:
            logger.exception(f"[TG] Error handling message: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
        finally:
            total_time = time.time() - start_time
            logger.info(f"[TG] Total handle_message time: {total_time:.2f}s")
            stop_typing.set()
            await typing_task
    
    def setup(self) -> Application:
        """Set up the bot application with command handlers."""
        self.app = Application.builder().token(self.token).build()
        
        # Command handlers
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(CommandHandler("status", self._handle_status))
        self.app.add_handler(CommandHandler("threads", self._handle_threads))
        self.app.add_handler(CommandHandler("kill", self._handle_kill))
        self.app.add_handler(CommandHandler("cleanup", self._handle_cleanup))
        self.app.add_handler(CommandHandler("tokens", self._handle_tokens))
        self.app.add_handler(CommandHandler("compact", self._handle_compact))
        self.app.add_handler(CommandHandler("verbose", self._handle_verbose))
        self.app.add_handler(CommandHandler("subagent", self._handle_subagent))
        
        # Message handler (non-command text)
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
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
        
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
