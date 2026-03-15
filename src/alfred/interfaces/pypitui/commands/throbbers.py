"""/throbbers command - Show throbber showcase overlay."""

import asyncio
from typing import TYPE_CHECKING, override

from alfred.interfaces.pypitui.commands.base import Command
from alfred.interfaces.pypitui.throbber_overlay import ThrobberOverlay
from pypitui import Key, OverlayOptions, matches_key

if TYPE_CHECKING:
    from collections.abc import Callable

    from alfred.interfaces.pypitui.tui import AlfredTUI
    from pypitui import OverlayHandle


class ThrobbersCommand(Command):
    """Show throbber showcase overlay."""

    name: str = "throbbers"
    description: str = "Show throbber animations"

    def __init__(self) -> None:
        self._overlay: ThrobberOverlay | None = None
        self._handle: OverlayHandle | None = None
        self._running: bool = False
        self._task: asyncio.Task[None] | None = None
        self._remove_listener: Callable[[], None] | None = None

    @override
    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Show throbber showcase overlay."""
        if self._running:
            # Already running, ignore
            return True

        self._overlay = ThrobberOverlay(page=0)
        self._running = True

        # Show overlay centered, modal
        options = OverlayOptions(
            anchor="center",
            width=60,
            max_height=14,
        )
        self._handle = tui.tui.show_overlay(self._overlay, options)

        # Start animation loop
        self._task = asyncio.create_task(self._animate(tui))

        # Add input handler for navigation - store the removal function
        self._remove_listener = tui.tui.add_input_listener(lambda data: self._on_input(tui, data))

        return True

    async def _animate(self, tui: "AlfredTUI") -> None:
        """Animation loop for throbbers."""
        try:
            while self._running and self._overlay:
                if self._overlay.tick():
                    tui.tui.request_render()
                await asyncio.sleep(0.05)  # 20fps animation
        except asyncio.CancelledError:
            pass

    def _on_input(self, tui: "AlfredTUI", data: str) -> dict[str, bool] | None:
        """Handle navigation input.

        Returns:
            {"consume": True} to block input from reaching other handlers
        """
        if not self._running or not self._overlay:
            return None

        if matches_key(data, Key.escape) or data == "q":
            self._close(tui)
            return {"consume": True}

        if data == "n":
            if self._overlay.next_page():
                tui.tui.request_render()
            return {"consume": True}

        if data == "p":
            if self._overlay.prev_page():
                tui.tui.request_render()
            return {"consume": True}

        return None

    def _close(self, tui: "AlfredTUI") -> None:
        """Close the overlay and stop animation."""
        self._running = False

        if self._task:
            self._task.cancel()
            self._task = None

        if self._handle:
            self._handle.hide()
            self._handle = None

        # Remove input listener to prevent memory leaks
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None

        self._overlay = None
        tui.tui.request_render()
