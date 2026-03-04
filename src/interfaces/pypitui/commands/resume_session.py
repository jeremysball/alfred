"""/resume command - Resume an existing session."""

from typing import TYPE_CHECKING

from src.interfaces.pypitui.commands.base import Command

if TYPE_CHECKING:
    from src.interfaces.pypitui.tui import AlfredTUI


class ResumeSessionCommand(Command):
    """Resume an existing session."""

    name = "resume"
    description = "Resume session by ID"

    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Resume an existing session."""
        if not arg:
            tui._add_user_message(  # type: ignore[misc]
                "Usage: /resume <session_id>\nUse /sessions to see available sessions."
            )
            return True

        try:
            tui._clear_conversation()  # type: ignore[misc]
            tui.alfred.session_manager.resume_session(arg.strip())

            # Load all session messages into conversation
            tui._load_session_messages()  # type: ignore[misc]

            tui._update_status()  # type: ignore[misc]
        except ValueError as e:
            tui._add_user_message(f"Error: {e}")  # type: ignore[misc]
        return True
