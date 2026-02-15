"""Core dispatcher that routes messages and manages threads."""
import asyncio
import logging
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
        logger.info(f"[DISPATCHER] Message thread={thread_id}")
        
        # Load or create thread
        thread = await self.storage.load(thread_id)
        if not thread:
            thread = Thread(thread_id=thread_id, chat_id=chat_id)
            logger.info(f"[DISPATCHER] Created thread {thread_id}")
        
        # Add user message
        thread.add_message("user", message)
        
        try:
            # Get or start Pi process for this thread
            pi = await self.pi_manager.get_or_create(thread_id, self.workspace_dir)
            
            # Send to Pi and get response
            response = await pi.send_message(message)
            
            # Add assistant message
            thread.add_message("assistant", response)
            await self.storage.save(thread)
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"[DISPATCHER] Timeout thread={thread_id}")
            return "⏱️ Timeout. Try again."
        except Exception as e:
            logger.exception(f"[DISPATCHER] Error thread={thread_id}: {e}")
            return f"❌ Error: {str(e)}"
    
    async def handle_command(self, thread_id: str, command: str) -> str:
        """Handle slash commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/status":
            active = await self.pi_manager.list_active()
            stored = await self.storage.list_threads()
            return (
                f"🤖 Status\n\n"
                f"Active processes: {len(active)}\n"
                f"Stored threads: {len(stored)}\n\n"
                f"Active: {', '.join(active) or 'None'}"
            )
        
        elif cmd == "/threads":
            stored = await self.storage.list_threads()
            active = await self.pi_manager.list_active()
            
            lines = ["📋 Threads\n"]
            for tid in stored:
                status = "🟢" if tid in active else "⚪"
                lines.append(f"{status} {tid}")
            
            return "\n".join(lines) if stored else "No threads stored."
        
        elif cmd == "/kill":
            if len(parts) < 2:
                return "Usage: /kill <thread_id>"
            
            target = parts[1]
            killed = await self.pi_manager.kill_thread(target)
            
            if killed:
                return f"✅ Killed {target}"
            return f"❌ {target} not active"
        
        elif cmd == "/cleanup":
            active = await self.pi_manager.list_active()
            await self.pi_manager.cleanup()
            return f"✅ Killed {len(active)} processes"
        
        return f"Unknown command: {cmd}"
    
    async def spawn_subagent(
        self,
        chat_id: int,
        thread_id: str,
        task: str
    ) -> str:
        """Spawn a background sub-agent for a task."""
        logger.info(f"[DISPATCHER] Spawning sub-agent for thread={thread_id}")
        
        # Load parent thread
        parent = await self.storage.load(thread_id)
        if not parent:
            return "❌ Parent thread not found"
        
        # Create sub-agent thread ID
        subagent_id = f"{thread_id}_sub_{asyncio.get_event_loop().time()}"
        
        # Mark parent as having active subagent
        parent.active_subagent = subagent_id
        await self.storage.save(parent)
        
        # Start background task
        asyncio.create_task(
            self._run_subagent(chat_id, thread_id, subagent_id, task)
        )
        
        return f"🔄 Sub-agent {subagent_id} started"
    
    async def _run_subagent(
        self,
        chat_id: int,
        parent_thread_id: str,
        subagent_id: str,
        task: str
    ) -> None:
        """Run sub-agent in background."""
        logger.info(f"[SUBAGENT] {subagent_id} starting: {task[:50]}...")
        
        # Create sub-agent workspace
        subagent_workspace = self.workspace_dir / "subagents" / subagent_id
        subagent_workspace.mkdir(parents=True, exist_ok=True)
        
        try:
            # Get Pi process for sub-agent
            pi = await self.pi_manager.get_or_create(subagent_id, subagent_workspace)
            
            # Run task
            result = await pi.send_message(
                f"You are a sub-agent. Complete this task:\n\n{task}\n\n"
                f"Report results concisely."
            )
            
            # Save sub-agent thread
            subagent_thread = Thread(
                thread_id=subagent_id,
                chat_id=chat_id
            )
            subagent_thread.add_message("system", f"Task: {task}")
            subagent_thread.add_message("assistant", result)
            await self.storage.save(subagent_thread)
            
            logger.info(f"[SUBAGENT] {subagent_id} complete")
            
            # Update parent thread with result
            parent = await self.storage.load(parent_thread_id)
            if parent:
                parent.add_message("system", f"Sub-agent {subagent_id} result:\n{result}")
                parent.active_subagent = None
                await self.storage.save(parent)
                
        except Exception as e:
            logger.exception(f"[SUBAGENT] {subagent_id} failed: {e}")
        finally:
            # Cleanup
            await self.pi_manager.kill_thread(subagent_id)
    
    async def shutdown(self) -> None:
        """Clean shutdown."""
        await self.pi_manager.cleanup()
        logger.info("[DISPATCHER] Shutdown")
