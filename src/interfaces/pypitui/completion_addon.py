"""Completion menu addon for WrappedInput.

Uses a separate CompletionMenuComponent in the layout for rendering.
Updates the menu's options and visibility based on input changes.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from pypitui import Key, matches_key

if TYPE_CHECKING:
    from .completion_menu_component import CompletionMenuComponent
    from .wrapped_input import WrappedInput


class CompletionAddon:
    """Completion behavior using a separate menu component.

    Hooks into WrappedInput for input detection, updates a
    CompletionMenuComponent for display (which must be in the layout).
    """

    def __init__(
        self,
        input_component: "WrappedInput",
        provider: Callable[[str], list[tuple[str, str | None]]],
        menu_component: "CompletionMenuComponent",
        trigger: str = "/",
    ) -> None:
        self._input = input_component
        self._provider = provider
        self._menu = menu_component
        self._trigger = trigger
        self._last_text: str | None = None

        # Register hooks on WrappedInput
        # Input hook for consuming navigation keys
        self._input.add_input_hook(self._handle_input_hook)
        # Post-input hook for updating completion state after value changes
        self._input.add_post_input_hook(self._update_completion)

    def _handle_input_hook(self, data: str) -> bool:
        """Input hook wrapper that returns bool for consumption check."""
        result = self.handle_input(data)
        return result is not None and result.get("consume", False)

    def _update_completion(self) -> None:
        """Update completion state based on current input.

        Called via post-input hook so input value is already updated.
        """
        text = self._input.get_value()

        if text == self._last_text:
            return
        self._last_text = text

        if not text.startswith(self._trigger):
            if self._menu.is_open:
                self._menu.close()
            return

        options = self._provider(text)

        if options:
            self._menu.set_options(options)
            self._menu.open()
        else:
            if self._menu.is_open:
                self._menu.close()

    def handle_input(self, data: str) -> dict | None:
        """Handle input when menu is open.

        Returns {"consume": True} if key was handled, None otherwise.
        """
        if not self._menu.is_open:
            return None

        if matches_key(data, Key.tab):
            self._accept_completion()
            return {"consume": True}
        elif matches_key(data, Key.enter):
            # Accept completion but DON'T consume Enter - let it trigger submit
            self._accept_completion()
            return None  # Don't consume - let Input handle the Enter
        elif matches_key(data, Key.up):
            self._menu.move_up()
            return {"consume": True}
        elif matches_key(data, Key.down):
            self._menu.move_down()
            return {"consume": True}
        elif matches_key(data, Key.right):
            return self._accept_ghost_char()
        elif matches_key(data, Key.left):
            return self._reject_ghost_char()
        elif matches_key(data, Key.escape):
            self._menu.close()
            return {"consume": True}

        return None

    def _get_ghost_suffix(self) -> str | None:
        """Get the current ghost text suffix if available."""
        if not self._menu.is_open or not self._menu._options_prop:
            return None

        selected_value = self._menu._options_prop[self._menu.selected_index][0]
        current_text = self._input.get_value()

        if not selected_value.startswith(current_text):
            return None

        suffix = selected_value[len(current_text):]
        return suffix if suffix else None

    def _accept_ghost_char(self) -> dict | None:
        """Accept the first character of ghost text (right arrow behavior).

        Returns {"consume": True} if a ghost character was accepted.
        """
        ghost_suffix = self._get_ghost_suffix()
        if not ghost_suffix:
            return None

        # Accept the first character of the ghost suffix
        current_text = self._input.get_value()
        new_text = current_text + ghost_suffix[0]
        new_cursor = len(new_text)

        self._input.set_value(new_text)
        self._input.set_cursor_pos(new_cursor)
        self._last_text = new_text

        return {"consume": True}

    def _reject_ghost_char(self) -> dict | None:
        """Reject (back out) the last accepted ghost character (left arrow).

        Returns {"consume": True} if a character was removed.
        """
        if not self._menu.is_open or not self._menu._options_prop:
            return None

        selected_value = self._menu._options_prop[self._menu.selected_index][0]
        current_text = self._input.get_value()

        # Can only reject if we have accepted some characters beyond the trigger
        # and those characters match the start of the selected completion
        if not selected_value.startswith(current_text) or len(current_text) <= 1:
            return None

        # Check if we're still within the completion prefix
        # (i.e., the text we have is the start of selected_value)
        if current_text != selected_value[: len(current_text)]:
            return None

        # Remove the last character
        new_text = current_text[:-1]
        new_cursor = len(new_text)

        self._input.set_value(new_text)
        self._input.set_cursor_pos(new_cursor)
        self._last_text = new_text

        return {"consume": True}

    def _accept_completion(self) -> None:
        """Accept selected completion."""
        if not self._menu.is_open:
            return

        options = self._menu._options_prop
        if not options:
            self._menu.close()
            return

        selected_value = options[self._menu.selected_index][0]
        # Don't add trailing space - it causes race condition with rapid typing
        self._input.set_value(selected_value)
        self._input.set_cursor_pos(len(selected_value))
        self._last_text = selected_value
        self._menu.close()
        # Trigger submit after accepting completion
        if self._input.on_submit:
            self._input.on_submit(selected_value)
