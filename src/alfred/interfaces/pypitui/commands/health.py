"""/health command - Show system health status."""

import asyncio
from typing import TYPE_CHECKING

from alfred.embeddings.bge_provider import BGEProvider
from alfred.interfaces.pypitui.commands.base import Command

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.tui import AlfredTUI


class HealthCommand(Command):
    """Show system health status for session and memory systems."""

    name = "health"
    description = "Show system health status"

    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Show health status of Alfred's systems."""

        async def _fetch_and_display() -> None:
            """Async helper to fetch stats and display health info."""
            lines: list[str] = []

            # Get core services
            core = tui.alfred.core
            session_manager = core.session_manager
            embedder = core.embedder
            memory_store = getattr(core, "memory_store", None)
            store = session_manager.store

            # === Session System Status ===
            lines.append("📋 SESSION SYSTEM")
            lines.append("─" * 40)

            if session_manager.has_active_session():
                session = session_manager.get_current_cli_session()
                if session:
                    meta = session.meta
                    lines.append(f"  Current Session: {meta.session_id[:8]}...")
                    lines.append(f"  Messages: {meta.message_count}")
                    lines.append(f"  Status: {meta.status}")
                else:
                    lines.append("  Current Session: Loading...")
            else:
                lines.append("  Current Session: No active session")

            # Get total session count
            try:
                total_sessions = await store.count_sessions()
                lines.append(f"  Total Sessions: {total_sessions}")
            except Exception as e:
                lines.append(f"  Total Sessions: Error ({e})")

            lines.append("")

            # === Memory System Status ===
            lines.append("🧠 MEMORY SYSTEM")
            lines.append("─" * 40)

            # Get memory count
            memory_count = 0
            if memory_store:
                try:
                    exceeded, count = memory_store.check_memory_threshold(threshold=999999)
                    memory_count = count
                    lines.append(f"  Stored Memories: {count}")
                except Exception as e:
                    lines.append(f"  Stored Memories: Error ({e})")
            else:
                # Try to get from store directly
                try:
                    memory_count = await store.count_memories()
                    lines.append(f"  Stored Memories: {memory_count}")
                except Exception as e:
                    lines.append(f"  Stored Memories: Error ({e})")

            # Memory threshold warning
            if memory_count > 1000:
                lines.append(f"  ⚠️  Warning: {memory_count} memories (threshold: 1000)")

            lines.append("")

            # === Embedding System Status ===
            lines.append("🔢 EMBEDDING SYSTEM")
            lines.append("─" * 40)

            embedder_name = embedder.__class__.__name__
            lines.append(f"  Provider: {embedder_name}")
            lines.append(f"  Dimension: {embedder.dimension}")

            # Check if BGE model is loaded
            if isinstance(embedder, BGEProvider):
                # Access the private _model attribute to check load status
                model_loaded = getattr(embedder, "_model", None) is not None
                if model_loaded:
                    lines.append("  Model Status: ✅ Loaded")
                else:
                    lines.append("  Model Status: ⏳ Not loaded (will load on first use)")
            else:
                lines.append("  Model Status: ✅ API-based (no local model)")

            lines.append("")

            # === LLM Status ===
            lines.append("🤖 LLM SYSTEM")
            lines.append("─" * 40)
            lines.append(f"  Model: {tui.alfred.model_name}")

            lines.append("")

            # === Storage Status ===
            lines.append("💾 STORAGE")
            lines.append("─" * 40)
            try:
                db_path = store.db_path
                lines.append(f"  Database: {db_path}")

                # Check if sqlite-vec is available
                try:
                    import sqlite_vec  # noqa: F401

                    lines.append("  Vector Search: ✅ sqlite-vec available")
                except ImportError:
                    lines.append("  Vector Search: ❌ sqlite-vec not installed")
            except Exception as e:
                lines.append(f"  Database: Error ({e})")

            lines.append("")
            lines.append("Use /sessions to list all sessions")
            lines.append("Use /context to view current context details")

            # Add as system message
            tui._add_system_message("\n".join(lines))

        # Schedule async work
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(_fetch_and_display())
        except RuntimeError:
            # No event loop - run synchronously (shouldn't happen in TUI)
            tui._add_system_message("Error: No event loop available")

        return True
