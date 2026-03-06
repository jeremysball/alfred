"""Base class for TUI commands."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.tui import AlfredTUI


class Command(ABC):
    """Base class for TUI commands.

    Commands are executed when users type /<command> in the TUI.
    Each command receives the TUI instance and an optional argument.
    """

    name: str
    """Command name without the leading slash (e.g., 'new', 'resume')."""

    description: str
    """Brief description shown in completion menu."""

    @abstractmethod
    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Execute the command.

        Args:
            tui: The AlfredTUI instance for accessing state and UI.
            arg: Optional argument string (everything after the command name).

        Returns:
            True if the command was handled, False otherwise.
        """
        ...
