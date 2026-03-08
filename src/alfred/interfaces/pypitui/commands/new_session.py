"""/new command - Create a new session."""

import asyncio
from typing import TYPE_CHECKING

from alfred.interfaces.pypitui.commands.base import Command

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.tui import AlfredTUI


class NewSessionCommand(Command):
    """Create a new session."""

    name = "new"
    description = "Create new session"

    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Create a new session."""
        # Run async initialization in background task
        asyncio.create_task(self._execute_async(tui))
        return True

    async def _execute_async(self, tui: "AlfredTUI") -> None:
        """Async implementation of new session creation."""
        tui._clear_conversation()  # type: ignore[misc]
        tui.alfred.token_tracker.reset()
        session = await tui.alfred.core.session_manager.new_session_async()
        tui._add_user_message(f"New session created: {session.meta.session_id}")  # type: ignore[misc]
        tui._update_status()  # type: ignore[misc]
