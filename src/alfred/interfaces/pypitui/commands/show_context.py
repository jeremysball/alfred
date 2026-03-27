"""/context command - Show system context."""

import asyncio
import logging
from typing import Any

from alfred.interfaces.pypitui.commands.base import Command

logger = logging.getLogger(__name__)


class ShowContextCommand(Command):
    """Show current system context."""

    name = "context"
    description = "Show system context"

    def execute(self, tui: Any, arg: str | None) -> bool:
        """Show current system context."""
        from alfred.context_display import get_context_display

        logger.debug("ShowContextCommand: executing /context command")

        has_active_session = tui.alfred.core.session_manager.has_active_session()
        logger.debug("ShowContextCommand: has_active_session=%s", has_active_session)

        async def _fetch_and_display() -> None:
            """Async helper to fetch and display context."""
            try:
                # Get context data
                logger.debug("ShowContextCommand: fetching context data from Alfred")
                context_data = await get_context_display(tui.alfred)
                logger.debug(
                    "ShowContextCommand: context data fetched - total_tokens=%d, memories=%d, "
                    "session_messages=%d, tool_calls=%d",
                    context_data.get("total_tokens", 0),
                    context_data.get("memories", {}).get("total", 0),
                    context_data.get("session_history", {}).get("count", 0),
                    context_data.get("tool_calls", {}).get("count", 0),
                )

                # Build display text
                lines: list[str] = []

                if not has_active_session:
                    lines.append("No active session.")
                    lines.append("")

                warnings = [warning for warning in (context_data.get("warnings") or []) if warning]
                if not warnings:
                    blocked_context_files = context_data.get("blocked_context_files") or []
                    if blocked_context_files:
                        warnings = [f"Blocked context files: {', '.join(blocked_context_files)}"]

                if warnings:
                    lines.append("WARNING:")
                    lines.append("─" * 40)
                    for warning in warnings:
                        lines.append(f"  ! {warning}")
                    lines.append("")

                # System prompt section
                sys_prompt = context_data["system_prompt"]
                lines.append(f"SYSTEM PROMPT ({sys_prompt['total_tokens']:,} tokens)")
                lines.append("─" * 40)
                for section in sys_prompt["sections"]:
                    lines.append(f"  {section['name']}: {section['tokens']:,} tokens")
                lines.append("")

                # Memories section
                memories = context_data["memories"]
                lines.append(f"MEMORIES ({memories['displayed']} of {memories['total']} memories, {memories['tokens']:,} tokens)")
                lines.append("─" * 40)
                for mem in memories["items"]:
                    role = "User" if mem["role"] == "user" else "Assistant"
                    lines.append(f"  [{mem['timestamp']}] {role}: {mem['content']}")
                if memories["total"] > memories["displayed"]:
                    lines.append(f"  ... and {memories['total'] - memories['displayed']} more")
                lines.append("")

                # Session history section
                history = context_data["session_history"]
                lines.append(f"SESSION HISTORY ({history['count']} messages, {history['tokens']:,} tokens)")
                lines.append("─" * 40)
                for msg in history["messages"]:
                    role = msg["role"].capitalize()
                    lines.append(f"  {role}: {msg['content']}")
                lines.append("")

                # Tool calls section
                tool_calls = context_data["tool_calls"]
                if tool_calls["count"] > 0:
                    lines.append(f"RECENT TOOL CALLS ({tool_calls['count']} calls, {tool_calls['tokens']:,} tokens)")
                    lines.append("─" * 40)
                    for i, tc in enumerate(tool_calls["items"], 1):
                        status_icon = "✓" if tc["status"] == "success" else "✗"
                        args_str = ", ".join(f"{k}={v}" for k, v in tc["arguments"].items())
                        if len(args_str) > 50:
                            args_str = args_str[:47] + "..."
                        lines.append(f"  {i}. {status_icon} {tc['tool_name']}: {args_str}")
                        if tc["output"]:
                            output = tc["output"].replace("\n", " ")
                            if len(output) > 60:
                                output = output[:57] + "..."
                            lines.append(f"     → {output}")
                    lines.append("")

                # Self-model section
                self_model = context_data["self_model"]
                lines.append("ALFRED SELF-MODEL")
                lines.append("─" * 40)
                lines.append(f"  Identity: {self_model['identity']['name']} ({self_model['identity']['role']})")
                runtime = self_model['runtime']
                mode_str = "daemon" if runtime['daemon_mode'] else "interactive"
                lines.append(f"  Interface: {runtime['interface']} | Mode: {mode_str}")
                caps = self_model['capabilities']
                mem_status = "✓" if caps['memory_enabled'] else "✗"
                search_status = "✓" if caps['search_enabled'] else "✗"
                lines.append(f"  Capabilities: Memory {mem_status} | Search {search_status} | {caps['tools_count']} tools")
                pressure = self_model['context_pressure']
                tokens_str = f"~{pressure['approximate_tokens']:,} tokens" if pressure['approximate_tokens'] else "unknown tokens"
                lines.append(f"  Context: {pressure['message_count']} messages | {pressure['memory_count']} memories | {tokens_str}")
                lines.append("")

                # Total
                lines.append(f"TOTAL CONTEXT: ~{context_data['total_tokens']:,} tokens")

                logger.debug(
                    "ShowContextCommand: display built - %d lines, ~%d tokens total",
                    len(lines),
                    context_data['total_tokens'],
                )

                # Add as system message (no markdown to preserve formatting)
                tui._add_system_message("\n".join(lines))
                logger.debug("ShowContextCommand: context display added to TUI")

            except Exception as e:
                logger.exception("ShowContextCommand: error displaying context")
                tui._add_system_message(f"Error displaying context: {e}")

        # Schedule async work on event loop (we're already in async context)
        try:
            asyncio.get_running_loop()
            asyncio.create_task(_fetch_and_display())
        except RuntimeError:
            # No event loop running - this shouldn't happen in TUI
            tui._add_user_message("Error: No event loop available")

        return True
