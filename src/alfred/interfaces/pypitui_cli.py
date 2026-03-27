"""PyPiTUI-based CLI interface for Alfred.

This module re-exports components from the pypitui subpackage for backwards compatibility.

NOTE: As part of the pypitui v2 migration, many components have been removed or replaced.
The new interface uses pypitui v2 primitives directly. This module will be updated
once the new AlfredTUI implementation is complete.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alfred.interfaces.pypitui import (
    CompatTUI,
    HistoryManager,
    OverlayHandle,
    OverlayOptions,
    ProcessTerminal,
    ToastHandler,
    ToastManager,
    ToolCallInfo,
    add_toast,
    format_tokens,
)
from alfred.interfaces.pypitui.commands import (
    Command,
    HealthCommand,
    ListSessionsCommand,
    NewSessionCommand,
    ResumeSessionCommand,
    ShowContextCommand,
    ShowSessionCommand,
    ThrobbersCommand,
)

if TYPE_CHECKING:
    from alfred.alfred import Alfred


class AlfredTUI:
    """Minimal AlfredTUI stub for backwards compatibility during pypitui v2 migration.

    This is a temporary implementation that provides the expected interface
    while the full TUI rewrite is in progress. It uses CompatTUI under the hood.
    """

    def __init__(
        self,
        alfred: Alfred,
        toast_manager: ToastManager | None = None,
    ) -> None:
        """Initialize the Alfred TUI.

        Args:
            alfred: The Alfred instance to interact with
            toast_manager: Optional ToastManager for notifications
        """
        self.alfred = alfred
        self._toast_manager = toast_manager
        # Create terminal and CompatTUI internally
        self._terminal = ProcessTerminal()
        self._tui = CompatTUI(self._terminal)

    async def run(self) -> None:
        """Run the TUI main loop.

        This is a minimal stub that starts the TUI and runs a simple loop.
        The full implementation will be restored during the pypitui v2 migration.
        """
        self._tui.start()
        try:
            # Minimal implementation: just keep running until interrupted
            # The full TUI will render messages and handle input properly
            while True:
                # Check for terminal input
                seq = self._terminal.read_sequence(timeout=0.1)
                if seq:
                    # Handle Ctrl-C to exit
                    if seq == "\x03":  # Ctrl-C
                        break
                    # Pass to input handlers
                    self._tui.handle_input(seq)

                # Render frame
                self._tui.render_frame()
        finally:
            self._tui.stop()


__all__ = [
    # Main TUI class
    "AlfredTUI",
    # Compatibility layer
    "CompatTUI",
    "ProcessTerminal",
    "OverlayHandle",
    "OverlayOptions",
    # Commands
    "Command",
    "HealthCommand",
    "ListSessionsCommand",
    "NewSessionCommand",
    "ResumeSessionCommand",
    "ShowContextCommand",
    "ShowSessionCommand",
    "ThrobbersCommand",
    # Components
    "HistoryManager",
    "ToastManager",
    "ToastHandler",
    "ToolCallInfo",
    # Functions
    "add_toast",
    "format_tokens",
]
