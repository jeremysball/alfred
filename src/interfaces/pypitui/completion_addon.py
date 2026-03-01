"""Completion addon for composable command completion."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from pypitui import Key, matches_key

from .completion_menu import CompletionMenu

if TYPE_CHECKING:
    from .wrapped_input import WrappedInput


class CompletionAddon:
    """Composable completion behavior that attaches to WrappedInput.

    Uses WrappedInput's hook system to intercept keys and modify render output.
    """

    def __init__(
        self,
        input_component: "WrappedInput",
        provider: Callable[[str], list[tuple[str, str | None]]],
        trigger: str = "/",
        max_height: int = 5,
    ) -> None:
        """Attach completion behavior to input component.

        Args:
            input_component: The WrappedInput to attach completion to.
            provider: Function called on keystrokes matching trigger.
                     Takes current text, returns list of (value, description).
            trigger: Prefix that activates completion mode.
            max_height: Maximum menu height (renders upward from input).
        """
        self._input = input_component
        self._provider = provider
        self._trigger = trigger
        self._menu = CompletionMenu(max_height=max_height)
        self._last_text: str | None = None

        # Track previous menu state for detecting changes
        self._was_open = False
        self._prev_option_count = 0

        # Register hooks
        self._input.add_input_filter(self._handle_input)
        self._input.add_render_filter(self._handle_render)

    def _handle_input(self, key: str) -> bool:
        """Handle keyboard input when completion is active.

        Args:
            key: The keyboard input.

        Returns:
            True if the key was consumed, False to pass to input.
        """
        # If menu is open, handle navigation keys
        if self._menu.is_open:
            if matches_key(key, Key.tab) or matches_key(key, Key.enter):
                self._accept_completion()
                return True
            elif matches_key(key, Key.up):
                self._menu.move_up()
                return True
            elif matches_key(key, Key.down):
                self._menu.move_down()
                return True
            elif matches_key(key, Key.escape):
                self._menu.close()
                return True

        # Let the input process the key
        return False

    def _update_completion(self) -> None:
        """Update completion state based on current input."""
        text = self._input.get_value()

        # Only update if text changed
        if text == self._last_text:
            return
        self._last_text = text

        # Check if trigger matches
        if not text.startswith(self._trigger):
            self._menu.close()
            return

        # Call provider with current text
        options = self._provider(text)

        if options:
            self._menu.set_options(options)
            self._menu.open()
        else:
            self._menu.close()

    def _accept_completion(self) -> None:
        """Accept the currently selected completion."""
        if not self._menu.is_open:
            return

        # Get selected option
        options = self._menu._options
        if not options:
            return

        selected_value = options[self._menu.selected_index][0]

        # Insert completion value with trailing space
        self._input.set_value(selected_value + " ")
        self._input.set_cursor_pos(len(selected_value) + 1)

        # Update last_text so we don't re-trigger completion
        self._last_text = selected_value + " "

        # Close menu
        self._menu.close()

    def get_ghost_text(self) -> str | None:
        """Get ghost text for currently selected completion.

        Returns:
            The text to show as ghost (dimmed inline preview),
            or None if no completion is selected.
        """
        # Update completion state to ensure menu is current
        self._update_completion()

        if not self._menu.is_open or not self._menu._options:
            return None

        selected_value = self._menu._options[self._menu.selected_index][0]
        current_text = self._input.get_value()

        # Only show ghost if selected value starts with current text
        if selected_value.startswith(current_text) and len(selected_value) > len(current_text):
            return selected_value[len(current_text):]

        return None

    def _handle_render(self, lines: list[str], width: int) -> list[str]:
        """Prepend menu to input render output and inject ghost text.

        Args:
            lines: Input render lines.
            width: Render width.

        Returns:
            Menu lines followed by input lines with ghost text.
        """
        # Update completion state before rendering (text is now current)
        self._update_completion()

        # Detect menu state changes for re-render requests
        current_option_count = len(self._menu._options) if self._menu.is_open else 0
        state_changed = (
            self._was_open != self._menu.is_open
            or self._prev_option_count != current_option_count
        )
        self._was_open = self._menu.is_open
        self._prev_option_count = current_option_count

        # Inject ghost text into the last line (input line with cursor)
        ghost = self.get_ghost_text()
        if ghost and lines:
            # Replace the last line (input line) with ghost-injected version
            # Hide cursor and show ghost text dimmed
            input_line = lines[-1]
            # Remove cursor marker and reverse video codes (including cursor char)
            import re
            # Strip cursor marker APC sequence
            clean_line = re.sub(r'\x1b_pi:c\x07', '', input_line)
            # Strip reverse video block completely (remove cursor char)
            clean_line = re.sub(r'\x1b\[7m[^\x1b]*\x1b\[27m', '', clean_line)
            # Add ghost text with faint attribute
            ghost_line = f"{clean_line}\x1b[2m{ghost}\x1b[0m"
            lines = lines[:-1] + [ghost_line]

        if not self._menu.is_open:
            return lines

        menu_lines = self._menu.render(width)
        result = menu_lines + lines

        # Request full re-render if menu state changed
        if state_changed and hasattr(self._input, 'invalidate'):
            self._input.invalidate()

        return result
