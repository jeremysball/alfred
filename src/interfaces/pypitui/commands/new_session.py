"""/new command - Create a new session."""

from typing import TYPE_CHECKING

from src.interfaces.pypitui.commands.base import Command

if TYPE_CHECKING:
    from src.interfaces.pypitui.tui import AlfredTUI


class NewSessionCommand(Command):
    """Create a new session."""

    name = "new"
    description = "Create new session"

    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Create a new session."""
        tui._clear_conversation()
        tui.alfred.token_tracker.reset()
        session = tui.alfred.session_manager.new_session()
        tui._add_user_message(f"New session created: {session.meta.session_id}")
        tui._update_status()
        return True
