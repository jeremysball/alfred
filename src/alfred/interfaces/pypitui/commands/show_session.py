"""/session command - Show current session info."""

from typing import TYPE_CHECKING

from alfred.interfaces.pypitui.commands.base import Command

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.tui import AlfredTUI


class ShowSessionCommand(Command):
    """Show current session info."""

    name = "session"
    description = "Show current session info"

    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Show current session details."""
        if not tui.alfred.core.session_manager.has_active_session():
            tui._add_user_message("No active session.")
            return True

        session = tui.alfred.core.session_manager.get_current_cli_session()
        if not session:
            tui._add_user_message("No active session.")
            return True

        meta = session.meta
        created = meta.created_at.strftime("%Y-%m-%d %H:%M")
        last_active = meta.last_active.strftime("%Y-%m-%d %H:%M")

        tui._add_user_message(
            f"Current Session\n"
            f"ID: {meta.session_id}\n"
            f"Status: {meta.status}\n"
            f"Created: {created}\n"
            f"Last Active: {last_active}\n"
            f"Messages: {meta.message_count}"
        )
        return True
