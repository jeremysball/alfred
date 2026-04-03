"""/context command - Show system context."""

import asyncio
import logging
from typing import Any

from alfred.interfaces.pypitui.commands.base import Command

logger = logging.getLogger(__name__)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _preview_count_text(displayed: Any, total: Any, noun: str) -> str:
    displayed_count = _as_int(displayed)
    total_count = _as_int(total, displayed_count)
    return f"{displayed_count} displayed of {total_count} {noun}"


def _render_tool_outcome_lines(item: dict[str, Any], index: int) -> list[str]:
    summary = item.get("summary")
    if summary:
        return [f"  {index}. {summary}"]

    tool_name = str(item.get("tool_name", "tool"))
    status_icon = "✓" if item.get("status") == "success" else "✗"
    line = f"  {index}. {status_icon} {tool_name}"

    arguments = item.get("arguments")
    if isinstance(arguments, dict) and arguments:
        args_str = ", ".join(f"{k}={v}" for k, v in arguments.items())
        if len(args_str) > 50:
            args_str = args_str[:47] + "..."
        line += f": {args_str}"

    lines = [line]
    output = item.get("output")
    if output:
        output_text = str(output).replace("\n", " ")
        if len(output_text) > 60:
            output_text = output_text[:57] + "..."
        lines.append(f"     → {output_text}")

    return lines


def _render_conflicted_context_lines(item: dict[str, Any], index: int) -> list[str]:
    label = str(item.get("label") or item.get("name") or item.get("id") or "Unknown")
    reason = str(item.get("reason") or "Blocked context file")
    return [f"  {index}. {label}: {reason}"]


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
                session_history = context_data.get("session_history", {})
                tool_calls = context_data.get("tool_calls", {})
                logger.debug(
                    "ShowContextCommand: context data fetched - total_tokens=%d, memories=%d, session_messages=%d, tool_outcomes=%d",
                    context_data.get("total_tokens", 0),
                    context_data.get("memories", {}).get("total", 0),
                    session_history.get("displayed", session_history.get("count", 0)),
                    tool_calls.get("displayed", tool_calls.get("count", 0)),
                )

                # Build display text
                lines: list[str] = []

                if not has_active_session:
                    lines.append("No active session.")
                    lines.append("")

                warnings = [warning for warning in (context_data.get("warnings") or []) if warning]
                conflicted_context_files = context_data.get("conflicted_context_files") or []
                if not conflicted_context_files:
                    blocked_context_files = context_data.get("blocked_context_files") or []
                    if blocked_context_files:
                        conflicted_context_files = [{"label": name, "reason": "Blocked context file"} for name in blocked_context_files]

                if conflicted_context_files:
                    count = len(conflicted_context_files)
                    noun = "file" if count == 1 else "files"
                    lines.append(f"CONFLICTED MANAGED TEMPLATES ({count} {noun})")
                    lines.append("─" * 40)
                    for i, item in enumerate(conflicted_context_files, 1):
                        lines.extend(_render_conflicted_context_lines(item, i))
                    lines.append("")

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
                    section_label = section.get("label") or section.get("name") or "Unknown"
                    lines.append(f"  {section_label}: {int(section.get('tokens', 0)):,} tokens")
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
                history_displayed = _as_int(history.get("displayed", history.get("count", 0)))
                history_total = _as_int(history.get("total", history_displayed), history_displayed)
                lines.append(
                    f"SESSION HISTORY ({_preview_count_text(history_displayed, history_total, 'messages')}, "
                    f"{int(history.get('tokens', 0)):,} tokens)"
                )
                lines.append("─" * 40)
                for msg in history["messages"]:
                    role = msg["role"].capitalize()
                    lines.append(f"  {role}: {msg['content']}")
                lines.append("")

                # Tool calls section
                tool_calls = context_data["tool_calls"]
                tool_displayed = _as_int(tool_calls.get("displayed", tool_calls.get("count", 0)))
                tool_total = _as_int(tool_calls.get("total", tool_displayed), tool_displayed)
                if tool_displayed > 0:
                    lines.append(
                        f"RECENT TOOL OUTCOMES ({_preview_count_text(tool_displayed, tool_total, 'calls')}, "
                        f"{int(tool_calls.get('tokens', 0)):,} tokens)"
                    )
                    lines.append("─" * 40)
                    for i, tc in enumerate(tool_calls["items"], 1):
                        lines.extend(_render_tool_outcome_lines(tc, i))
                    lines.append("")

                # Self-model section
                self_model = context_data["self_model"]
                lines.append("ALFRED SELF-MODEL")
                lines.append("─" * 40)
                lines.append(f"  Identity: {self_model['identity']['name']} ({self_model['identity']['role']})")
                runtime = self_model["runtime"]
                mode_str = "daemon" if runtime["daemon_mode"] else "interactive"
                lines.append(f"  Interface: {runtime['interface']} | Mode: {mode_str}")
                caps = self_model["capabilities"]
                mem_status = "✓" if caps["memory_enabled"] else "✗"
                search_status = "✓" if caps["search_enabled"] else "✗"
                lines.append(f"  Capabilities: Memory {mem_status} | Search {search_status} | {caps['tools_count']} tools")
                pressure = self_model["context_pressure"]
                tokens_str = f"~{pressure['approximate_tokens']:,} tokens" if pressure["approximate_tokens"] else "unknown tokens"
                lines.append(f"  Context: {pressure['message_count']} messages | {pressure['memory_count']} memories | {tokens_str}")
                lines.append("")

                # Total
                lines.append(f"TOTAL CONTEXT: ~{context_data['total_tokens']:,} tokens")

                logger.debug(
                    "ShowContextCommand: display built - %d lines, ~%d tokens total",
                    len(lines),
                    context_data["total_tokens"],
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
