"""/resume command - Resume an existing session."""

import asyncio
from typing import TYPE_CHECKING

from alfred.interfaces.pypitui.commands.base import Command

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.tui import AlfredTUI


class ResumeSessionCommand(Command):
    """Resume an existing session."""

    name = "resume"
    description = "Resume session by ID"

    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Resume an existing session."""
        if not arg:
            tui._add_user_message("Usage: /resume <session_id>\nUse /sessions to see available sessions.")
            return True

        asyncio.create_task(self._execute_async(tui, arg.strip()))
        return True

    async def _execute_async(self, tui: "AlfredTUI", session_id: str) -> None:
        """Async implementation of resume session."""
        try:
            tui._clear_conversation()
            await tui.alfred.core.session_manager.resume_session_async(session_id)

            # Load all session messages into conversation
            await tui._load_session_messages()

            tui._update_status()
        except ValueError as e:
            tui._add_user_message(f"Error: {e}")
