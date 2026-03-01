"""Completion menu using pypitui 0.3.0 overlay system - Version 2.

This version properly hooks into WrappedInput for input detection
while using TUI overlays for rendering.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from pypitui import (
    Container,
    Key,
    OverlayHandle,
    OverlayMargin,
    OverlayOptions,
    Text,
    matches_key,
)

from .completion_menu import CompletionMenu

if TYPE_CHECKING:
    from pypitui import TUI

    from .wrapped_input import WrappedInput


class CompletionOverlayV2:
    """Completion behavior using pypitui 0.3.0 overlay system.

    Hooks into WrappedInput for input detection, uses TUI overlays for rendering.
    """

    def __init__(
        self,
        tui: "TUI",
        input_component: "WrappedInput",
        provider: Callable[[str], list[tuple[str, str | None]]],
        trigger: str = "/",
        max_height: int = 5,
    ) -> None:
        self._tui = tui
        self._input = input_component
        self._provider = provider
        self._trigger = trigger
        self._menu = CompletionMenu(max_height=max_height)
        self._overlay_handle: OverlayHandle | None = None
        self._last_text: str | None = None

        # Register hooks on WrappedInput
        self._input.add_input_filter(self._on_input)
        self._input.add_render_filter(self._on_render)

    def _on_render(self, lines: list[str], width: int) -> list[str]:
        """Update completion state after input has processed changes."""
        self._update_completion()
        return lines

    def _on_input(self, data: str) -> bool:
        """Handle input - return True to consume, False to pass through."""
        # First update completion state (text has changed)
        self._update_completion()

        # If menu is open, handle navigation
        if not self._menu.is_open:
            return False

        if matches_key(data, Key.tab) or matches_key(data, Key.enter):
            self._accept_completion()
            return True
        elif matches_key(data, Key.up):
            self._menu.move_up()
            self._refresh_overlay()
            return True
        elif matches_key(data, Key.down):
            self._menu.move_down()
            self._refresh_overlay()
            return True
        elif matches_key(data, Key.escape):
            self._close_overlay()
            return True

        return False

    def _update_completion(self) -> None:
        """Update completion state based on current input."""
        text = self._input.get_value()

        if text == self._last_text:
            return
        self._last_text = text

        if not text.startswith(self._trigger):
            self._close_overlay()
            return

        options = self._provider(text)

        if options:
            self._menu.set_options(options)
            self._menu.open()
            self._show_overlay()
        else:
            self._close_overlay()

    def _show_overlay(self) -> None:
        """Show completion menu as overlay."""
        if self._overlay_handle is not None:
            return

        options = OverlayOptions(
            width=50,
            max_height=self._menu._max_height + 2,
            anchor="bottom-center",
            offset_y=-1,
            margin=OverlayMargin(bottom=1, left=2, right=2, top=0),
        )

        menu_lines = self._menu.render(50)
        overlay_content = Container()
        for line in menu_lines:
            overlay_content.add_child(Text(line))

        self._overlay_handle = self._tui.show_overlay(overlay_content, options)

    def _refresh_overlay(self) -> None:
        """Refresh overlay after selection change."""
        if self._overlay_handle is None:
            return

        self._overlay_handle.hide()
        self._overlay_handle = None
        self._show_overlay()

    def _close_overlay(self) -> None:
        """Close completion overlay."""
        self._menu.close()
        if self._overlay_handle is not None:
            self._overlay_handle.hide()
            self._overlay_handle = None

    def _accept_completion(self) -> None:
        """Accept selected completion."""
        if not self._menu.is_open:
            return

        options = self._menu._options
        if not options:
            self._close_overlay()
            return

        selected_value = options[self._menu.selected_index][0]
        self._input.set_value(selected_value + " ")
        self._input.set_cursor_pos(len(selected_value) + 1)
        self._last_text = selected_value + " "
        self._close_overlay()
