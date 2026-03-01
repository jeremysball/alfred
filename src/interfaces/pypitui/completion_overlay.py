"""Completion menu using pypitui 0.3.0 overlay system.

This is an improved version of CompletionAddon that uses the new overlay
API instead of render filters for cleaner separation of concerns.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from pypitui import (
    Key,
    OverlayHandle,
    OverlayMargin,
    OverlayOptions,
    matches_key,
)

from .completion_menu import CompletionMenu

if TYPE_CHECKING:
    from pypitui import TUI

    from .wrapped_input import WrappedInput


class CompletionOverlay:
    """Completion behavior using pypitui overlay system.

    Shows completion menu as a floating overlay above the input,
    providing cleaner separation between input and menu rendering.
    """

    def __init__(
        self,
        tui: "TUI",
        input_component: "WrappedInput",
        provider: Callable[[str], list[tuple[str, str | None]]],
        trigger: str = "/",
        max_height: int = 5,
    ) -> None:
        """Initialize completion overlay.

        Args:
            tui: The TUI instance for showing overlays.
            input_component: The input component to attach completion to.
            provider: Function called on keystrokes matching trigger.
            trigger: Prefix that activates completion mode.
            max_height: Maximum menu height.
        """
        self._tui = tui
        self._input = input_component
        self._provider = provider
        self._trigger = trigger
        self._menu = CompletionMenu(max_height=max_height)
        self._overlay_handle: OverlayHandle | None = None
        self._last_text: str | None = None

        # Register input listener on TUI
        self._remove_listener = tui.add_input_listener(self._handle_input)

    def _handle_input(self, data: str) -> dict | None:
        """Intercept input for completion navigation.

        Args:
            data: Raw keyboard input.

        Returns:
            {"consume": True} to block input from reaching input component,
            None to allow input through.
        """
        # Update completion state first
        self._update_completion()

        # If menu is not open and input doesn't match trigger, let it through
        if not self._menu.is_open:
            return None

        # Handle menu navigation keys using matches_key for proper sequence matching
        if matches_key(data, Key.tab) or matches_key(data, Key.enter):
            self._accept_completion()
            return {"consume": True}
        elif matches_key(data, Key.up):
            self._menu.move_up()
            self._refresh_overlay()
            return {"consume": True}
        elif matches_key(data, Key.down):
            self._menu.move_down()
            self._refresh_overlay()
            return {"consume": True}
        elif matches_key(data, Key.escape):
            self._close_overlay()
            return {"consume": True}

        # Let other keys through (they'll update completion via _update_completion)
        return None

    def _update_completion(self) -> None:
        """Update completion state based on current input."""
        text = self._input.get_value()

        # Only update if text changed
        if text == self._last_text:
            return
        self._last_text = text

        # Check if trigger matches
        if not text.startswith(self._trigger):
            self._close_overlay()
            return

        # Call provider with current text
        options = self._provider(text)

        if options:
            self._menu.set_options(options)
            self._menu.open()
            self._show_overlay()
        else:
            self._close_overlay()

    def _show_overlay(self) -> None:
        """Show the completion menu as an overlay."""
        if self._overlay_handle is not None:
            # Already showing, will refresh in _refresh_overlay
            return

        # Calculate position above input
        # For now, use center-bottom anchor as approximation
        options = OverlayOptions(
            width=50,  # Will be adjusted based on content
            max_height=self._menu._max_height + 2,  # +2 for borders
            anchor="bottom-center",
            offset_y=-1,  # Just above input
            margin=OverlayMargin(bottom=1, left=2, right=2, top=0),
        )

        # Render menu content
        menu_lines = self._menu.render(50)
        from pypitui import Container, Text

        overlay_content = Container()
        for line in menu_lines:
            overlay_content.add_child(Text(line))

        self._overlay_handle = self._tui.show_overlay(overlay_content, options)

    def _refresh_overlay(self) -> None:
        """Refresh overlay content after selection change."""
        if self._overlay_handle is None or not self._menu.is_open:
            return

        # Hide and re-show with updated content
        # In a full implementation, we'd update the overlay content directly
        self._overlay_handle.hide()
        self._overlay_handle = None
        self._show_overlay()

    def _close_overlay(self) -> None:
        """Close the completion overlay."""
        self._menu.close()
        if self._overlay_handle is not None:
            self._overlay_handle.hide()
            self._overlay_handle = None

    def _accept_completion(self) -> None:
        """Accept the currently selected completion."""
        if not self._menu.is_open:
            return

        options = self._menu._options
        if not options:
            self._close_overlay()
            return

        selected_value = options[self._menu.selected_index][0]

        # Insert completion value with trailing space
        self._input.set_value(selected_value + " ")
        self._input.set_cursor_pos(len(selected_value) + 1)

        # Update last_text so we don't re-trigger completion
        self._last_text = selected_value + " "

        self._close_overlay()

    def cleanup(self) -> None:
        """Clean up resources when done."""
        self._close_overlay()
        if self._remove_listener:
            self._remove_listener()
