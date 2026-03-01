"""Completion menu addon for WrappedInput.

Uses render filter to prepend menu lines to input output.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from pypitui import Key, matches_key

from .completion_menu import CompletionMenu

if TYPE_CHECKING:
    from .wrapped_input import WrappedInput


class CompletionAddon:
    """Completion behavior using render filter.

    Hooks into WrappedInput via render filter to prepend menu lines.
    Uses callback for re-render requests when state changes without
    input value changing (e.g., navigation).
    """

    def __init__(
        self,
        input_component: "WrappedInput",
        provider: Callable[[str], list[tuple[str, str | None]]],
        trigger: str = "/",
        max_height: int = 5,
        on_state_change: Callable[[], None] | None = None,
    ) -> None:
        self._input = input_component
        self._provider = provider
        self._trigger = trigger
        self._menu = CompletionMenu(max_height=max_height)
        self._last_text: str | None = None
        self._menu_lines: list[str] = []
        self._on_state_change = on_state_change

        # Register render filter on WrappedInput
        self._input.add_render_filter(self._on_render)

    def _on_render(self, lines: list[str], width: int) -> list[str]:
        """Prepend menu lines to input render output."""
        # Update completion state based on current input
        self._update_completion(width)

        # If menu is open, re-render and prepend its lines
        # Always re-render to pick up selection changes from navigation
        if self._menu.is_open:
            self._menu_lines = self._menu.render(width)
            return self._menu_lines + lines

        return lines

    def _update_completion(self, width: int) -> None:
        """Update completion state."""
        text = self._input.get_value()

        if text == self._last_text:
            return
        self._last_text = text

        if not text.startswith(self._trigger):
            if self._menu.is_open:
                self._menu.close()
                self._menu_lines = []
            return

        options = self._provider(text)

        if options:
            self._menu.set_options(options)
            self._menu.open()
            self._menu_lines = self._menu.render(width)
        else:
            if self._menu.is_open:
                self._menu.close()
                self._menu_lines = []

    def _notify_state_change(self) -> None:
        """Notify that menu state changed and re-render is needed."""
        if self._on_state_change:
            self._on_state_change()

    def handle_input(self, data: str) -> dict | None:
        """Handle input when menu is open.

        Returns {"consume": True} if key was handled, None otherwise.
        """
        if not self._menu.is_open:
            return None

        if matches_key(data, Key.tab) or matches_key(data, Key.enter):
            self._accept_completion()
            return {"consume": True}
        elif matches_key(data, Key.up):
            self._menu.move_up()
            self._notify_state_change()
            return {"consume": True}
        elif matches_key(data, Key.down):
            self._menu.move_down()
            self._notify_state_change()
            return {"consume": True}
        elif matches_key(data, Key.escape):
            self._menu.close()
            self._menu_lines = []
            self._notify_state_change()
            return {"consume": True}

        return None

    def _accept_completion(self) -> None:
        """Accept selected completion."""
        if not self._menu.is_open:
            return

        options = self._menu._options
        if not options:
            self._menu.close()
            self._menu_lines = []
            self._notify_state_change()
            return

        selected_value = options[self._menu.selected_index][0]
        self._input.set_value(selected_value + " ")
        self._input.set_cursor_pos(len(selected_value) + 1)
        self._last_text = selected_value + " "
        self._menu.close()
        self._menu_lines = []
        self._notify_state_change()
