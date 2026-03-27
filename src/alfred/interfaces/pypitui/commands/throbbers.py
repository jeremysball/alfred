"""/throbbers command - Show throbber showcase overlay.

NOTE: Throbbers have been removed as part of the pypitui v2 migration.
This command is now a no-op and will be removed in a future update.
"""

from typing import TYPE_CHECKING, override

from alfred.interfaces.pypitui.commands.base import Command

if TYPE_CHECKING:
    pass


class ThrobbersCommand(Command):
    """Show throbber showcase overlay."""

    name: str = "throbbers"
    description: str = "Show throbber animations (deprecated)"

    @override
    def execute(self, tui: object, arg: str | None) -> bool:
        """Show throbber showcase overlay."""
        # Throbbers removed in pypitui v2 migration
        return True
