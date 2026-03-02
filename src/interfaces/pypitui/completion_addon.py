"""Completion menu addon for WrappedInput.

Uses render hook to prepend menu lines to input output.
Includes ghost text (inline preview) of selected completion.
"""

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from pypitui import CURSOR_MARKER, Key, matches_key

from src.interfaces.pypitui.ansi import BRIGHT_BLACK, RESET, REVERSE

from .completion_menu import CompletionMenu

if TYPE_CHECKING:
    from .wrapped_input import WrappedInput


class CompletionAddon:
    """Completion behavior using render hook.

    Hooks into WrappedInput via render hook to prepend menu lines.
    Uses component invalidation bubbling for efficient re-renders.
    """

    def __init__(
        self,
        input_component: "WrappedInput",
        provider: Callable[[str], list[tuple[str, str | None]]],
        trigger: str = "/",
        max_height: int = 5,
    ) -> None:
        self._input = input_component
        self._provider = provider
        self._trigger = trigger
        self._menu = CompletionMenu(max_height=max_height)
        self._last_text: str | None = None

        # Register hooks on WrappedInput
        self._input.add_render_hook(self._on_render)
        self._input.add_input_hook(self._handle_input_hook)

    def _on_render(self, lines: list[str], width: int) -> list[str]:
        """Prepend menu lines and inject ghost text into input line."""
        # Update completion state based on current input
        self._update_completion(width)

        # Inject ghost text into the input line (last line)
        if lines and self._menu.is_open:
            lines = self._inject_ghost_text(lines)

        # If menu is open, prepend menu lines
        if self._menu.is_open:
            menu_lines = self._menu.render(width)
            return menu_lines + lines

        return lines

    def _inject_ghost_text(self, lines: list[str]) -> list[str]:
        """Inject ghost text (inline preview) at cursor position on input line.

        Ghost text shows the remaining characters of the selected completion,
        appearing inline at the cursor position with dim styling. The cursor
        is moved to the end of the ghost text.
        """
        if not self._menu._options:
            return lines

        selected_value = self._menu._options[self._menu.selected_index][0]
        current_text = self._input.get_value()

        # Only show ghost if selected value starts with current text
        if not selected_value.startswith(current_text):
            return lines

        ghost_suffix = selected_value[len(current_text):]
        if not ghost_suffix:
            return lines

        # Modify the last line (input line with cursor)
        input_line = lines[-1]

        # Find cursor position - look for CURSOR_MARKER and reverse video
        # Pattern: CURSOR_MARKER + REVERSE + char + RESET
        cursor_pattern = (
            f"({re.escape(CURSOR_MARKER)})({re.escape(REVERSE)})"
            f"([^\x1b]*)({re.escape(RESET)})"
        )
        match = re.search(cursor_pattern, input_line)

        if match:
            # Structure: before + CURSOR_MARKER + REVERSE + char + RESET + after
            # We want: before + ghost_text + CURSOR_MARKER + REVERSE + " " + RESET + after
            # This puts ghost text inline, then cursor at end of ghost text
            before = input_line[:match.start()]  # Text before cursor
            after = input_line[match.end():]     # Text after RESET
            # Reconstruct: typed text + ghost + cursor (on space) + rest
            ghost_line = (
                f"{before}{BRIGHT_BLACK}{ghost_suffix}{RESET}"
                f"{CURSOR_MARKER}{REVERSE} {RESET}{after}"
            )
            return lines[:-1] + [ghost_line]

        # No cursor found, return unchanged (e.g., in test environments)
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
                self._input.invalidate()
            return

        options = self._provider(text)

        if options:
            had_menu = self._menu.is_open
            self._menu.set_options(options)
            self._menu.open()
            if not had_menu:
                # Menu just opened - invalidate for render
                self._input.invalidate()
        else:
            if self._menu.is_open:
                self._menu.close()
                self._input.invalidate()

    def _handle_input_hook(self, data: str) -> bool:
        """Input hook wrapper that returns bool for consumption check."""
        result = self.handle_input(data)
        return result is not None and result.get("consume", False)

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
            self._input.invalidate()
            return {"consume": True}
        elif matches_key(data, Key.down):
            self._menu.move_down()
            self._input.invalidate()
            return {"consume": True}
        elif matches_key(data, Key.escape):
            self._menu.close()
            self._input.invalidate()
            return {"consume": True}

        return None

    def _accept_completion(self) -> None:
        """Accept selected completion."""
        if not self._menu.is_open:
            return

        options = self._menu._options
        if not options:
            self._menu.close()
            self._input.invalidate()
            return

        selected_value = options[self._menu.selected_index][0]
        self._input.set_value(selected_value + " ")
        self._input.set_cursor_pos(len(selected_value) + 1)
        self._last_text = selected_value + " "
        self._menu.close()
        self._input.invalidate()
