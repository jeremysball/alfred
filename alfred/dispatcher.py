"""Core dispatcher that routes messages and manages threads."""
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

from alfred.context_loader import ContextLoader
from alfred.models import Thread
from alfred.pi_manager import PiManager
from alfred.storage import ThreadStorage
from alfred.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


from alfred.heartbeat import Heartbeat


class Dispatcher:
    """Main dispatcher that routes messages and manages threads."""

    def __init__(
        self,
        workspace_dir: Path,
        threads_dir: Path,
        pi_manager: PiManager,
        token_tracker: TokenTracker | None = None,
        heartbeat: Heartbeat | None = None
    ):
        self.workspace_dir = workspace_dir
        self.storage = ThreadStorage(threads_dir)
        self.pi_manager = pi_manager
        self.token_tracker = token_tracker
        self.heartbeat = heartbeat
        self.context_loader = ContextLoader(workspace_dir)

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
            # Load system prompt from context files
            system_prompt = self.context_loader.get_system_prompt()
            logger.info(f"[DISPATCHER] Loaded system prompt ({len(system_prompt)} chars)")

            # Send to Pi and get response
            t0 = time.time()
            response = await self.pi_manager.send_message(
                thread_id, self.workspace_dir, message, system_prompt
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

        elif cmd == "/tokens":
            return await self._get_token_stats()

        elif cmd == "/compact":
            custom_prompt = " ".join(parts[1:]) if len(parts) > 1 else None
            return await self._compact_thread(thread_id, custom_prompt)

        return f"Unknown command: {cmd}"

    async def spawn_subagent(
        self,
        chat_id: int,
        thread_id: str,
        task: str
    ) -> str:
        """Spawn a background sub-agent for a task."""
        logger.info(f"[DISPATCHER] Spawning sub-agent for thread={thread_id}")

        parent = await self.storage.load(thread_id)
        if not parent:
            return "❌ Parent thread not found"

        subagent_id = f"{thread_id}_sub_{asyncio.get_event_loop().time()}"

        parent.active_subagent = subagent_id
        await self.storage.save(parent)

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

        subagent_workspace = self.workspace_dir / "subagents" / subagent_id
        subagent_workspace.mkdir(parents=True, exist_ok=True)

        try:
            result = await self.pi_manager.send_message(
                subagent_id, subagent_workspace,
                f"You are a sub-agent. Complete this task:\n\n{task}\n\n"
                f"Report results concisely."
            )

            subagent_thread = Thread(
                thread_id=subagent_id,
                chat_id=chat_id
            )
            subagent_thread.add_message("system", f"Task: {task}")
            subagent_thread.add_message("assistant", result)
            await self.storage.save(subagent_thread)

            logger.info(f"[SUBAGENT] {subagent_id} complete")

            parent = await self.storage.load(parent_thread_id)
            if parent:
                parent.add_message("system", f"Sub-agent {subagent_id} result:\n{result}")
                parent.active_subagent = None
                await self.storage.save(parent)

        except Exception as e:
            logger.exception(f"[SUBAGENT] {subagent_id} failed: {e}")
        finally:
            await self.pi_manager.kill_thread(subagent_id)

    async def _get_full_status(self) -> str:
        """Get comprehensive system status."""
        import os
        from datetime import datetime

        lines = ["🤖 Alfred Status\n"]

        lines.append("📦 Bot")
        lines.append("  Version: 0.1.0")
        lines.append(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        if self.token_tracker:
            session = self.token_tracker.get_session_stats()
            lines.append("💰 Session Tokens")
            lines.append(f"  Requests: {session['requests']}")
            lines.append(f"  Total: {session['total_tokens']:,}")
            lines.append(f"  Input: {session['input_tokens']:,}")
            lines.append(f"  Output: {session['output_tokens']:,}")
            if session['cache_read'] > 0:
                lines.append(f"  Cache: {session['cache_read']:,}")
            if session['last_model']:
                lines.append(f"  Last model: {session['last_model']}")
            lines.append("")

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

        memory_files = list(self.workspace_dir.glob("memory/*.md")) if (self.workspace_dir / "memory").exists() else []
        skills_count = len(list((self.workspace_dir / "skills").glob("*/SKILL.md"))) if (self.workspace_dir / "skills").exists() else 0

        lines.append("📁 Workspace")
        lines.append(f"  Path: {self.workspace_dir}")
        lines.append(f"  Memory files: {len(memory_files)}")
        lines.append(f"  Skills loaded: {skills_count}")
        lines.append("")

        lines.append("⚙️ Configuration")
        lines.append(f"  Provider: {self.pi_manager.llm_provider}")
        lines.append(f"  Model: {self.pi_manager.llm_model or 'default'}")
        lines.append(f"  Timeout: {self.pi_manager.timeout}s")
        lines.append(f"  Thinking level: {getattr(self.pi_manager, 'thinking_level', 'default')}")
        lines.append("")

        if self.heartbeat:
            hb_status = self.heartbeat.get_status()
            lines.append("💓 Heartbeat")
            lines.append(f"  Status: {'✅' if hb_status['running'] else '❌'}")
            lines.append(f"  Interval: {hb_status['interval']}s")
            if hb_status['last_heartbeat']:
                lines.append(f"  Last: {hb_status['last_heartbeat'].split('T')[1].split('.')[0]}")
            lines.append("")

        lines.append("🔧 Features")
        embeddings_available = "✅" if os.getenv("OPENAI_API_KEY") else "❌"
        streaming_available = "✅" if getattr(self.pi_manager, 'streaming_enabled', False) else "❌"
        lines.append(f"  Embeddings: {embeddings_available}")
        lines.append(f"  Streaming: {streaming_available}")
        lines.append("")

        lines.append("Use /threads for detailed thread list")
        return "\n".join(lines)

    async def _get_token_stats(self) -> str:
        """Get token usage statistics."""
        if not self.token_tracker:
            return "❌ Token tracking not enabled"

        stats = self.token_tracker.get_daily_stats()

        lines = ["💰 Token Usage Today\n"]
        lines.append(f"📊 Requests: {stats['requests']}")
        lines.append(f"📝 Total tokens: {stats['total_tokens']:,}")
        lines.append(f"   Input: {stats['input_tokens']:,}")
        lines.append(f"   Output: {stats['output_tokens']:,}")
        lines.append(f"   Cache: {stats.get('cache_read', 0):,}")

        if stats['by_provider']:
            lines.append("\n🏢 By Provider:")
            for provider, data in stats['by_provider'].items():
                lines.append(f"  {provider}: {data['tokens']:,} tokens ({data['requests']} reqs)")

        if stats['by_thread']:
            lines.append("\n💬 Top Threads:")
            sorted_threads = sorted(
                stats['by_thread'].items(),
                key=lambda x: x[1]['tokens'],
                reverse=True
            )[:5]
            for tid, data in sorted_threads:
                lines.append(f"  {tid[:20]}...: {data['tokens']:,} tokens")

        return "\n".join(lines)

    async def _compact_thread(self, thread_id: str, custom_prompt: Optional[str] = None) -> str:
        """Compact current thread context into a summary."""
        try:
            thread = await self.storage.load(thread_id)
            if not thread or len(thread.messages) < 2:
                return "📭 No conversation to compact"

            lines = []
            for msg in thread.messages:
                prefix = "User" if msg.role == "user" else "Assistant"
                lines.append(f"{prefix}: {msg.content}")
            conversation = "\n\n".join(lines)

            if len(conversation) < 500:
                return "📭 Conversation too short to compact"

            prompt = custom_prompt or """Summarize this conversation concisely. Capture:
- Key decisions made
- Important context shared
- Action items or follow-ups
- Current state/topic

Be brief but complete."""

            compaction_request = f"{prompt}\n\n---\n\nConversation:\n\n{conversation}"

            summary = await self.pi_manager.send_message(
                f"{thread_id}_compact",
                self.workspace_dir,
                compaction_request
            )

            thread.messages = []
            thread.add_message("system", f"[COMPACTED] Previous conversation summary:\n\n{summary}")
            await self.storage.save(thread)

            original_msgs = len(lines)
            summary_len = len(summary)
            savings = (1 - summary_len / len(conversation)) * 100

            return (
                f"✅ Compacted thread\n"
                f"   {original_msgs} messages → summary\n"
                f"   ~{savings:.0f}% size reduction\n"
                f"   Summary: {summary[:200]}..."
            )

        except Exception as e:
            logger.exception(f"Error compacting thread: {e}")
            return f"❌ Error: {str(e)}"

    async def shutdown(self) -> None:
        """Clean shutdown."""
        await self.pi_manager.cleanup()
        logger.info("[DISPATCHER] Shutdown")
