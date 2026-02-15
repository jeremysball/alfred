"""Core dispatcher that routes messages and manages threads."""
import asyncio
import logging
import time
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
        start_time = time.time()
        logger.info(f"[DISPATCHER] Message thread={thread_id}, len={len(message)}")
        
        # Load or create thread
        t0 = time.time()
        thread = await self.storage.load(thread_id)
        if not thread:
            thread = Thread(thread_id=thread_id, chat_id=chat_id)
            logger.info(f"[DISPATCHER] Created thread {thread_id}")
        else:
            logger.info(f"[DISPATCHER] Loaded thread {thread_id} ({len(thread.messages)} messages)")
        logger.debug(f"[DISPATCHER] Thread load took {time.time() - t0:.2f}s")
        
        # Add user message
        thread.add_message("user", message)
        
        try:
            # Send to Pi and get response
            t0 = time.time()
            response = await self.pi_manager.send_message(
                thread_id, self.workspace_dir, message
            )
            pi_time = time.time() - t0
            logger.info(f"[DISPATCHER] Pi send_message took {pi_time:.2f}s")
            
            # Add assistant message
            thread.add_message("assistant", response)
            
            t0 = time.time()
            await self.storage.save(thread)
            logger.debug(f"[DISPATCHER] Thread save took {time.time() - t0:.2f}s")
            
            total_time = time.time() - start_time
            logger.info(f"[DISPATCHER] Total request time: {total_time:.2f}s")
            
            return response
            
        except asyncio.TimeoutError:
            total_time = time.time() - start_time
            logger.error(f"[DISPATCHER] Timeout after {total_time:.2f}s thread={thread_id}")
            return f"⏱️ Timeout after {total_time:.1f}s. Try again."
        except Exception as e:
            total_time = time.time() - start_time
            logger.exception(f"[DISPATCHER] Error after {total_time:.2f}s thread={thread_id}: {e}")
            return f"❌ Error after {total_time:.1f}s: {str(e)}"
    
    async def handle_command(self, thread_id: str, command: str) -> str:
        """Handle slash commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/status":
            return await self._get_full_status()
        
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
            # Run task
            result = await self.pi_manager.send_message(
                subagent_id, subagent_workspace,
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
    
    async def _get_full_status(self) -> str:
        """Get comprehensive system status."""
        from datetime import datetime
        import os

        lines = ["🤖 OpenClaw Pi Status\n"]

        # Bot info
        lines.append("📦 Bot")
        lines.append(f"  Version: 0.1.0")
        lines.append(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Threads stats
        active = await self.pi_manager.list_active()
        stored = await self.storage.list_threads()
        total_messages = 0
        for tid in stored:
            thread = await self.storage.load(tid)
            if thread:
                total_messages += len(thread.messages)

        lines.append("💬 Threads")
        lines.append(f"  Active: {len(active)}")
        lines.append(f"  Stored: {len(stored)}")
        lines.append(f"  Total messages: {total_messages}")
        if active:
            lines.append(f"  Processing: {', '.join(active[:3])}{'...' if len(active) > 3 else ''}")
        lines.append("")

        # Workspace info
        memory_files = list(self.workspace_dir.glob("memory/*.md")) if (self.workspace_dir / "memory").exists() else []
        skills_count = len(list((self.workspace_dir / "skills").glob("*/SKILL.md"))) if (self.workspace_dir / "skills").exists() else 0

        lines.append("📁 Workspace")
        lines.append(f"  Path: {self.workspace_dir}")
        lines.append(f"  Memory files: {len(memory_files)}")
        lines.append(f"  Skills loaded: {skills_count}")
        lines.append("")

        # Configuration
        lines.append("⚙️ Configuration")
        lines.append(f"  Provider: {self.pi_manager.llm_provider}")
        lines.append(f"  Model: {self.pi_manager.llm_model or 'default'}")
        lines.append(f"  Timeout: {self.pi_manager.timeout}s")
        lines.append("")

        # Features
        lines.append("🔧 Features")
        embeddings_available = "✅" if os.getenv("OPENAI_API_KEY") else "❌"
        lines.append(f"  Embeddings: {embeddings_available}")
        lines.append("")

        lines.append("Use /threads for detailed thread list")
        return "\n".join(lines)

    async def shutdown(self) -> None:
        """Clean shutdown."""
        await self.pi_manager.cleanup()
        logger.info("[DISPATCHER] Shutdown")
