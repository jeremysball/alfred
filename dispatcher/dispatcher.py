"""Core dispatcher that routes messages and manages threads."""
import asyncio
import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from dispatcher.models import Thread
from dispatcher.storage import ThreadStorage
from dispatcher.llm_api import LLMApi

logger = logging.getLogger(__name__)


class Dispatcher:
    """Main dispatcher that routes messages and manages threads."""
    
    def __init__(
        self,
        workspace_dir: Path,
        threads_dir: Path,
        llm_provider: str = "zai",
        llm_api_key: str = "",
        llm_model: str = "",
        timeout: int = 300
    ):
        self.workspace_dir = workspace_dir
        self.storage = ThreadStorage(threads_dir)
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.timeout = timeout
    
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
            # Build messages for LLM
            messages = self._build_messages(thread)
            
            # Call LLM directly
            response = await LLMApi.complete(
                provider=self.llm_provider,
                api_key=self.llm_api_key,
                model=self.llm_model,
                messages=messages,
                timeout=self.timeout
            )
            
            # Add assistant message
            thread.add_message("assistant", response)
            
            # Save thread state
            await self.storage.save(thread)
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout in thread {thread_id}")
            return "⏱️ Request timed out. Try again."
        except Exception as e:
            logger.exception(f"Error in thread {thread_id}")
            return f"❌ Error: {str(e)}"
    
    async def handle_message_streaming(
        self,
        chat_id: int,
        thread_id: str,
        message: str
    ) -> AsyncGenerator[str, None]:
        """Handle incoming message, yield response."""
        logger.info(f"Handling streaming message for thread {thread_id}")
        
        # Check dispatcher commands (non-streaming)
        if message.startswith("/"):
            response = await self._handle_command(thread_id, message)
            yield response
            return
        
        # Use non-streaming for now
        response = await self.handle_message(chat_id, thread_id, message)
        yield response
    
    def _build_messages(self, thread: Thread) -> list[dict[str, str]]:
        """Build messages list for LLM from thread."""
        messages = []
        
        # Add system prompt
        system_prompt = self._load_system_prompt()
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        for msg in thread.messages:
            messages.append({"role": msg.role, "content": msg.content})
        
        return messages
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from workspace."""
        prompt_path = self.workspace_dir / "SYSTEM.md"
        if prompt_path.exists():
            return prompt_path.read_text()
        return "You are a helpful assistant."
    
    async def _handle_command(self, thread_id: str, command: str) -> str:
        """Handle dispatcher commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/status":
            threads = await self.storage.list_threads()
            return f"Stored threads: {len(threads)}\n{chr(10).join(threads[:10])}"
        
        elif cmd == "/threads":
            threads = await self.storage.list_threads()
            return f"Threads: {', '.join(threads) or 'None'}"
        
        elif cmd == "/help":
            return (
                "🤖 OpenClaw Dispatcher\n\n"
                "Commands:\n"
                "/status — Show stored threads\n"
                "/threads — List all threads\n"
                "/help — Show this message"
            )
        
        return f"Unknown command: {cmd}"
    
    async def shutdown(self) -> None:
        """Clean shutdown."""
        logger.info("Dispatcher shutdown complete")
