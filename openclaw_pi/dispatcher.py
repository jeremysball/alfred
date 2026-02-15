"""Core dispatcher that routes messages and manages threads."""
import asyncio
import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from openclaw_pi.models import Thread
from openclaw_pi.storage import ThreadStorage
from openclaw_pi.pi_manager import PiManager

logger = logging.getLogger(__name__)


class Dispatcher:
    """Main dispatcher that routes messages and manages threads."""
    
    def __init__(
        self,
        workspace_dir: Path,
        threads_dir: Path,
        pi_manager: PiManager
    ):
        self.workspace_dir = workspace_dir
        self.storage = ThreadStorage(threads_dir)
        self.pi_manager = pi_manager
    
    async def handle_message(
        self,
        chat_id: int,
        thread_id: str,
        message: str
    ) -> str:
        """Handle incoming message, return response."""
        logger.info(f"[DISPATCHER] Handling message for thread {thread_id}")
        logger.info(f"[DISPATCHER] Chat ID: {chat_id}, Message length: {len(message)} chars")
        logger.debug(f"[DISPATCHER] Message content: {message[:200]}...")
        
        # Check dispatcher commands
        if message.startswith("/"):
            logger.info(f"[DISPATCHER] Processing command: {message}")
            return await self._handle_command(thread_id, message)
        
        # Load or create thread
        logger.debug(f"[DISPATCHER] Loading thread {thread_id} from storage...")
        thread = await self.storage.load(thread_id)
        if not thread:
            logger.info(f"[DISPATCHER] Creating new thread {thread_id}")
            thread = Thread(thread_id=thread_id, chat_id=chat_id)
        else:
            logger.info(f"[DISPATCHER] Loaded existing thread {thread_id} with {len(thread.messages)} messages")
        
        # Add user message
        thread.add_message("user", message)
        
        try:
            # Get pi subprocess for this thread
            logger.debug(f"[DISPATCHER] Getting PiSubprocess for thread {thread_id}...")
            pi = await self.pi_manager.get_or_create(thread_id, self.workspace_dir)
            logger.info(f"[DISPATCHER] Got PiSubprocess, sending message to pi...")
            
            # Send to pi and get response
            response = await pi.send_message(message)
            
            # Add assistant message
            thread.add_message("assistant", response)
            
            # Save thread state
            logger.debug(f"[DISPATCHER] Saving thread {thread_id} state...")
            await self.storage.save(thread)
            logger.info(f"[DISPATCHER] Thread {thread_id} saved successfully")
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"[DISPATCHER] Timeout in thread {thread_id}")
            return "⏱️ Request timed out. Try again."
        except Exception as e:
            logger.exception(f"[DISPATCHER] Error in thread {thread_id}: {e}")
            return f"❌ Error: {str(e)}"
    
    async def handle_message_streaming(
        self,
        chat_id: int,
        thread_id: str,
        message: str
    ) -> AsyncGenerator[str, None]:
        """Handle incoming message, yield response."""
        # Just use non-streaming for now
        response = await self.handle_message(chat_id, thread_id, message)
        yield response
    
    async def _handle_command(self, thread_id: str, command: str) -> str:
        """Handle dispatcher commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/status":
            active = await self.pi_manager.list_active()
            stored = await self.storage.list_threads()
            return f"Active threads: {len(active)} | Stored threads: {len(stored)}"
        
        elif cmd == "/threads":
            threads = await self.storage.list_threads()
            return f"Threads: {', '.join(threads) or 'None'}"
        
        elif cmd == "/kill":
            if len(parts) < 2:
                return "Usage: /kill <thread_id>"
            target_thread = parts[1]
            killed = await self.pi_manager.kill_thread(target_thread)
            if killed:
                return f"✅ Killed thread: {target_thread}"
            return f"❌ Thread not found: {target_thread}"
        
        elif cmd == "/cleanup":
            await self.pi_manager.cleanup()
            return "✅ Cleaned up all active threads"
        
        elif cmd == "/help":
            return (
                "🤖 OpenClaw Dispatcher\n\n"
                "Commands:\n"
                "/status — Show active and stored threads\n"
                "/threads — List all stored threads\n"
                "/kill <id> — Kill a thread's process\n"
                "/cleanup — Kill all active processes\n"
                "/help — This message"
            )
        
        return f"Unknown command: {cmd}"
    
    async def shutdown(self) -> None:
        """Clean shutdown."""
        await self.pi_manager.cleanup()
        logger.info("Dispatcher shutdown complete")
