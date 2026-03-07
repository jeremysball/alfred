"""Completion system with longest-trigger-wins semantics.

Multiple (trigger, provider) pairs can be registered. When the input
text changes, the longest matching trigger wins and its provider is used.
"""

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from pypitui import Key, matches_key

if TYPE_CHECKING:
    from .completion_menu_component import CompletionMenuComponent
    from .wrapped_input import WrappedInput


class CompletionManager:
    """Manages multiple completion triggers with longest-match semantics.

    Only one trigger is active at a time - the one with the longest
    matching prefix. This prevents conflicts between overlapping triggers
    like "/" and "/resume ".
    """

    # Debounce configuration
    _debounce_delay_ms: int = 50
    _pending_update_time: float = 0

    def __init__(
        self,
        input_component: "WrappedInput",
        menu_component: "CompletionMenuComponent",
    ) -> None:
        """Initialize completion manager.

        Args:
            input_component: The input field to watch.
            menu_component: Shared menu component for displaying options.
        """
        self._input = input_component
        self._menu = menu_component
        self._triggers: list[tuple[str, Callable[[str], list[tuple[str, str | None]]]]] = []
        self._last_text: str | None = None
        self._active_trigger: str | None = None

        # Register hooks on WrappedInput
        self._input.add_input_hook(self._handle_input_hook)
        self._input.add_post_input_hook(self._update_completion)

    def register(
        self,
        trigger: str,
        provider: Callable[[str], list[tuple[str, str | None]]],
    ) -> None:
        """Register a completion trigger and provider.

        Args:
            trigger: The prefix that activates this completion (e.g., "/" or "/resume ").
            provider: Function that takes input text and returns (value, description) tuples.

        Note:
            Longer triggers take precedence. If both "/" and "/resume " match,
            "/resume " wins because it's longer.
        """
        self._triggers.append((trigger, provider))
        # Sort by trigger length descending (longest first)
        self._triggers.sort(key=lambda x: len(x[0]), reverse=True)

    def _find_active_trigger(
        self, text: str
    ) -> tuple[str | None, Callable[[str], list[tuple[str, str | None]]] | None]:
        """Find the longest matching trigger for the given text.

        Returns:
            Tuple of (trigger, provider) or (None, None) if no match.
        """
        for trigger, provider in self._triggers:
            if text.startswith(trigger):
                return trigger, provider
        return None, None

    def _handle_input_hook(self, data: str) -> bool:
        """Input hook wrapper that returns bool for consumption check."""
        result = self.handle_input(data)
        return result is not None and result.get("consume", False)

    def _update_completion(self) -> None:
        """Update completion state based on current input."""
        text = self._input.get_value()

        if text == self._last_text:
            return
        self._last_text = text

        # Find the longest matching trigger
        trigger, provider = self._find_active_trigger(text)

        if trigger is None or provider is None:
            # No trigger matches - close menu
            if self._menu.is_open:
                self._menu.close()
            self._active_trigger = None
            return

        # Get options from the winning provider
        options = provider(text)

        if options:
            self._menu.set_options(options)
            self._menu.open()
            self._active_trigger = trigger
        else:
            if self._menu.is_open:
                self._menu.close()
            self._active_trigger = None

    def handle_input(self, data: str) -> dict[str, bool] | None:
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
            return None
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
            self._active_trigger = None
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

        suffix = selected_value[len(current_text) :]
        return suffix if suffix else None

    def _accept_ghost_char(self) -> dict[str, bool] | None:
        """Accept the first character of ghost text (right arrow behavior).

        Returns {"consume": True} if a ghost character was accepted.
        """
        ghost_suffix = self._get_ghost_suffix()
        if not ghost_suffix:
            return None

        current_text = self._input.get_value()
        new_text = current_text + ghost_suffix[0]
        new_cursor = len(new_text)

        self._input.set_value(new_text)
        self._input.set_cursor_pos(new_cursor)
        self._last_text = new_text

        return {"consume": True}

    def _reject_ghost_char(self) -> dict[str, bool] | None:
        """Reject (back out) the last accepted ghost character (left arrow).

        Returns {"consume": True} if a character was removed.
        """
        if not self._menu.is_open or not self._menu._options_prop:
            return None

        selected_value = self._menu._options_prop[self._menu.selected_index][0]
        current_text = self._input.get_value()

        if not selected_value.startswith(current_text) or len(current_text) <= 1:
            return None

        if current_text != selected_value[: len(current_text)]:
            return None

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
            self._active_trigger = None
            return

        selected_value = options[self._menu.selected_index][0]
        self._input.set_value(selected_value)
        self._input.set_cursor_pos(len(selected_value))
        self._last_text = selected_value
        self._menu.close()
        self._active_trigger = None

        # NOTE: We do NOT call on_submit here. When this is triggered by
        # Enter key, the Enter propagates to pypitui's Input which calls
        # on_submit naturally. Calling it here would cause double-submit.

    def check_pending_update(self) -> None:
        """Check if a pending update should be executed (debounce mechanism)."""
        if self._pending_update_time and time.time() > self._pending_update_time:
            self._pending_update_time = 0
            self._update_completion()


# Backward compatibility alias
CompletionAddon = CompletionManager
