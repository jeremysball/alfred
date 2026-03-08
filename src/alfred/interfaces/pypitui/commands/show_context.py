"""/context command - Show system context."""

import asyncio
from typing import TYPE_CHECKING

from alfred.interfaces.pypitui.commands.base import Command

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.tui import AlfredTUI


class ShowContextCommand(Command):
    """Show current system context."""

    name = "context"
    description = "Show system context"

    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Show current system context."""
        from alfred.context_display import get_context_display

        if not tui.alfred.core.session_manager.has_active_session():
            tui._add_system_message("No active session.")  # type: ignore[misc]
            return True

        async def _fetch_and_display() -> None:
            """Async helper to fetch and display context."""
            try:
                # Get context data
                context_data = await get_context_display(tui.alfred)

                # Build display text
                lines: list[str] = []

                # System prompt section
                sys_prompt = context_data["system_prompt"]
                lines.append(f"SYSTEM PROMPT ({sys_prompt['total_tokens']:,} tokens)")
                lines.append("─" * 40)
                for section in sys_prompt["sections"]:
                    lines.append(f"  {section['name']}: {section['tokens']:,} tokens")
                lines.append("")

                # Memories section
                memories = context_data["memories"]
                lines.append(
                    f"MEMORIES ({memories['displayed']} of {memories['total']} memories, "
                    f"{memories['tokens']:,} tokens)"
                )
                lines.append("─" * 40)
                for mem in memories["items"]:
                    role = "User" if mem["role"] == "user" else "Assistant"
                    lines.append(f"  [{mem['timestamp']}] {role}: {mem['content']}")
                if memories["total"] > memories["displayed"]:
                    lines.append(f"  ... and {memories['total'] - memories['displayed']} more")
                lines.append("")

                # Session history section
                history = context_data["session_history"]
                lines.append(
                    f"SESSION HISTORY ({history['count']} messages, {history['tokens']:,} tokens)"
                )
                lines.append("─" * 40)
                for msg in history["messages"]:
                    role = msg["role"].capitalize()
                    lines.append(f"  {role}: {msg['content']}")
                lines.append("")

                # Tool calls section
                tool_calls = context_data["tool_calls"]
                if tool_calls["count"] > 0:
                    lines.append(
                        f"RECENT TOOL CALLS ({tool_calls['count']} calls, "
                        f"{tool_calls['tokens']:,} tokens)"
                    )
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

                # Total
                lines.append(f"TOTAL CONTEXT: ~{context_data['total_tokens']:,} tokens")

                # Add as system message (no markdown to preserve formatting)
                tui._add_system_message("\n".join(lines))  # type: ignore[misc]

            except Exception as e:
                tui._add_system_message(f"Error displaying context: {e}")  # type: ignore[misc]

        # Schedule async work on event loop (we're already in async context)
        try:
            asyncio.get_running_loop()
            asyncio.create_task(_fetch_and_display())
        except RuntimeError:
            # No event loop running - this shouldn't happen in TUI
            tui._add_user_message("Error: No event loop available")  # type: ignore[misc]

        return True
