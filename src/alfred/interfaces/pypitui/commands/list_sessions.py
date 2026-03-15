"""/sessions command - List all sessions."""

import asyncio
from typing import TYPE_CHECKING

from alfred.interfaces.pypitui.commands.base import Command

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.tui import AlfredTUI


class ListSessionsCommand(Command):
    """List all sessions."""

    name = "sessions"
    description = "List all sessions"

    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """List all sessions."""
        asyncio.create_task(self._execute_async(tui))
        return True

    async def _execute_async(self, tui: "AlfredTUI") -> None:
        """Async implementation of list sessions."""
        sessions = await tui.alfred.core.session_manager.list_sessions_async()
        if not sessions:
            tui._add_user_message("No sessions found.")
            return

        # Build output using non-breaking spaces to prevent word wrapping
        lines: list[str] = []

        current_id = None
        current_session = None
        if tui.alfred.core.session_manager.has_active_session():
            current_session = tui.alfred.core.session_manager.get_current_cli_session()
            if current_session:
                current_id = current_session.meta.session_id

        for meta in sessions[:20]:
            created = meta.created_at.strftime("%Y-%m-%d %H:%M")
            marker = " (current)" if meta.session_id == current_id else ""
            # Use cached session's message count for current session (more up-to-date)
            msg_count = meta.message_count
            if meta.session_id == current_id and current_session:
                msg_count = current_session.meta.message_count
            # Use non-breaking space (\xa0) between fields to prevent wrapping
            line = f"{meta.session_id}\xa0\xa0{created}\xa0\xa0{msg_count} msgs{marker}"
            lines.append(line)

        if len(sessions) > 20:
            lines.append(f"... and {len(sessions) - 20} more")

        tui._add_user_message("\n".join(lines))
