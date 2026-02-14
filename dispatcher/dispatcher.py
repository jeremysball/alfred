"""Core dispatcher that routes messages and manages threads."""
import asyncio
import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from dispatcher.models import Thread
from dispatcher.storage import ThreadStorage
from dispatcher.pi_manager import PiManager

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
        logger.info(f"Handling message for thread {thread_id}")
        
        # Check dispatcher commands
        if message.startswith("/"):
            return await self._handle_command(thread_id, message)
        
        # Load or create thread
        thread = await self.storage.load(thread_id)
        if not thread:
            thread = Thread(thread_id=thread_id, chat_id=chat_id)
        
        # Add user message
        thread.add_message("user", message)
        
        try:
            # Get or create pi subprocess for this thread
            pi = await self.pi_manager.get_or_create(
                thread_id,
                self.workspace_dir
            )
            
            # Send to pi and get response
            response = await pi.send_message(message)
            
            # Add assistant message
            thread.add_message("assistant", response)
            
            # Save thread state
            await self.storage.save(thread)
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout in thread {thread_id}")
            await self.pi_manager.kill_thread(thread_id)
            return "⏱️ Request timed out. Process killed. Try again."
        except Exception as e:
            logger.exception(f"Error in thread {thread_id}")
            return f"❌ Error: {str(e)}"
    
    async def handle_message_streaming(
        self,
        chat_id: int,
        thread_id: str,
        message: str
    ) -> AsyncGenerator[str, None]:
        """Handle incoming message, yield response chunks."""
        logger.info(f"Handling streaming message for thread {thread_id}")
        
        # Check dispatcher commands (non-streaming)
        if message.startswith("/"):
            response = await self._handle_command(thread_id, message)
            yield response
            return
        
        # Load or create thread
        thread = await self.storage.load(thread_id)
        if not thread:
            thread = Thread(thread_id=thread_id, chat_id=chat_id)
        
        # Add user message
        thread.add_message("user", message)
        
        try:
            # Get pi subprocess
            pi = await self.pi_manager.get_or_create(thread_id, self.workspace_dir)
            
            # Get full response (pi doesn't support true streaming yet)
            full_response = await pi.send_message(message)
            
            # Stream word by word for visual effect
            words = full_response.split()
            current = ""
            for i, word in enumerate(words):
                current += word + " "
                if i % 5 == 0 or i == len(words) - 1:
                    yield current
                    await asyncio.sleep(0.05)
            
            # Add assistant message
            thread.add_message("assistant", full_response)
            await self.storage.save(thread)
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout in thread {thread_id}")
            await self.pi_manager.kill_thread(thread_id)
            yield "⏱️ Request timed out. Process killed. Try again."
        except Exception as e:
            logger.exception(f"Error in thread {thread_id}")
            yield f"❌ Error: {str(e)}"
    
    async def _handle_command(self, thread_id: str, command: str) -> str:
        """Handle dispatcher commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/status":
            threads = await self.storage.list_threads()
            active = await self.pi_manager.list_active()
            return f"Active threads: {len(active)}\nStored threads: {len(threads)}\n{chr(10).join(active[:10])}"
        
        elif cmd == "/kill":
            if len(parts) < 2:
                return "Usage: /kill <thread_id>"
            target = parts[1]
            killed = await self.pi_manager.kill_thread(target)
            return f"Killed thread {target}" if killed else f"Thread {target} not found"
        
        elif cmd == "/threads":
            threads = await self.storage.list_threads()
            return f"Threads: {', '.join(threads) or 'None'}"
        
        elif cmd == "/cleanup":
            await self.pi_manager.cleanup()
            return "Cleaned up all processes"
        
        return f"Unknown command: {cmd}"
    
    async def shutdown(self) -> None:
        """Clean shutdown."""
        await self.pi_manager.cleanup()
        logger.info("Dispatcher shutdown complete")
