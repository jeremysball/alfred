"""WrappedInput component with display-line navigation.

Wraps pypitui's Input to add up/down arrow navigation across
display lines (handles wrapped text).

Uses character-based wrapping (not word-based) to maintain 1:1
position mapping between text cursor and display position.

Shows ALL display lines at once, with cursor on the appropriate line.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from pypitui import CURSOR_MARKER, Component, Focusable, Input, Key, matches_key
from pypitui.utils import truncate_to_width

from src.interfaces.ansi import (
    BRIGHT_WHITE,
    ON_BLUE,
    ON_GREEN,
    ON_RED,
    RESET,
    REVERSE,
)

if TYPE_CHECKING:
    from .completion_addon import CompletionManager
    from .completion_menu_component import CompletionMenuComponent


class WrappedInput(Component, Focusable):
    """Text input with display-line navigation for wrapped text.

    Wraps pypitui's Input component and adds:
    - Up/down arrow navigation across wrapped display lines
    - Maintains display column during vertical movement
    - Shows all display lines with cursor on correct line

    Uses character-based wrapping (not word-based) for reliable
    position mapping.

    Usage:
        inp = WrappedInput(placeholder="Type here...")
        inp.on_submit = lambda text: print(f"Submitted: {text}")

        # In render loop:
        lines = inp.render(width=80)  # Returns all wrapped lines
        # Handle input:
        inp.handle_input(data)
    """

    @property
    def is_static(self) -> bool:
        """Input field is fixed at the bottom and should not scroll."""
        return True

    def __init__(self, placeholder: str = "", cursor_color: str = "reverse") -> None:
        """Initialize WrappedInput.

        Args:
            placeholder: Placeholder text when empty and unfocused.
            cursor_color: Cursor color style ("reverse", "green", "red", "blue").
        """
        super().__init__()
        self._input = Input(placeholder=placeholder)
        self._input.on_submit = self._on_submit
        self._display_column = 0  # Desired column for vertical movement
        self._last_width = 80  # Last render width
        self._cursor_color = cursor_color

        # Callbacks
        self.on_submit: Callable | None = None
        self.on_cancel: Callable | None = None

        # Hook filters for composable behaviors
        self._input_hooks: list[Callable[[str], bool]] = []
        self._render_hooks: list[Callable[[list[str], int], list[str]]] = []
        self._post_input_hooks: list[Callable[[], None]] = []

    def add_input_hook(self, hook_fn: Callable[[str], bool]) -> None:
        """Register an input filter.

        Filters are called in order before normal input processing.
        If a filter returns True, the key is consumed and not processed further.

        Args:
            hook_fn: Function taking key string, returning True if consumed.
        """
        self._input_hooks.append(hook_fn)

    def add_render_hook(self, hook_fn: Callable[[list[str], int], list[str]]) -> None:
        """Register a render filter.

        Filters are applied in order to transform rendered output lines.

        Args:
            hook_fn: Function taking lines and width, returning modified lines.
        """
        self._render_hooks.append(hook_fn)

    def add_post_input_hook(self, hook_fn: Callable[[], None]) -> None:
        """Register a hook that runs after input is processed.

        Use this when you need to react to input changes after the value
        has been updated (e.g., for completion menus).

        Args:
            hook_fn: Function taking no arguments, called after input processing.
        """
        self._post_input_hooks.append(hook_fn)

    def with_completion_component(
        self,
        provider: Callable[[str], list[tuple[str, str | None]]],
        menu_component: "CompletionMenuComponent",
        trigger: str = "/",
    ) -> "WrappedInput":
        """Add command completion using a separate menu component.

        The menu_component must be added to the TUI layout separately.
        It will be shown/hidden based on input changes.

        Args:
            provider: Function that takes current text and returns
                     list of (value, description) tuples.
            menu_component: CompletionMenuComponent to control (must be in layout).
            trigger: Prefix that triggers completion (default: "/").

        Returns:
            Self for method chaining.

        Note:
            If called multiple times, the longest matching trigger wins.
            Use setup_completion() for cleaner multi-trigger setup.

        Example:
            menu = CompletionMenuComponent()
            tui.add_child(menu)  # Add to layout
            input_field.with_completion_component(my_provider, menu, trigger="/")
        """
        from src.interfaces.pypitui.completion_addon import CompletionManager

        # Lazily create manager on first call
        if not hasattr(self, "_completion_manager"):
            self._completion_manager = CompletionManager(self, menu_component)

        self._completion_manager.register(trigger, provider)
        return self

    def setup_completion(
        self,
        menu_component: "CompletionMenuComponent",
    ) -> "CompletionManager":
        """Set up completion with a shared menu component.

        Use this when you have multiple triggers. Returns the manager
        so you can call register() for each trigger.

        Args:
            menu_component: Shared menu component for all completions.

        Returns:
            CompletionManager to register triggers with.

        Example:
            menu = CompletionMenuComponent()
            tui.add_child(menu)
            manager = input_field.setup_completion(menu)
            manager.register("/", command_provider)
            manager.register("/resume ", session_id_provider)
        """
        from src.interfaces.pypitui.completion_addon import CompletionManager

        self._completion_manager = CompletionManager(self, menu_component)
        return self._completion_manager

    @property
    def focused(self) -> bool:
        """Whether this component has focus."""
        return self._input.focused

    @focused.setter
    def focused(self, value: bool) -> None:
        """Set focus state."""
        self._input.focused = value

    def get_value(self) -> str:
        """Get current input value."""
        return self._input.get_value()

    def set_value(self, text: str) -> None:
        """Set input value."""
        self._input.set_value(text)

    def set_cursor_pos(self, pos: int) -> None:
        """Set cursor position directly."""
        max_pos = len(self.get_value())
        self._input._cursor_pos = max(0, min(pos, max_pos))  # type: ignore[attr-defined]

    @property
    def _cursor_pos(self) -> int:
        """Get current cursor position."""
        return int(self._input._cursor_pos)  # type: ignore[attr-defined]

    @_cursor_pos.setter
    def _cursor_pos(self, value: int) -> None:
        """Set cursor position."""
        self._input._cursor_pos = value  # type: ignore[attr-defined]

    def render(self, width: int) -> list[str]:
        """Render input showing all display lines with cursor.

        Args:
            width: Terminal width in columns.

        Returns:
            List of display lines, with cursor marker on the appropriate line.
        """
        self._last_width = width
        text = self.get_value()

        if not text and not self.focused:
            # Show placeholder
            result = self._input.render(width)
            # Apply render filters
            for hook_fn in self._render_hooks:
                result = hook_fn(result, width)
            return result

        if width <= 0:
            return [text] if text else [""]

        # Split text into display lines
        display_lines = []
        for i in range(0, len(text), width):
            display_lines.append(text[i : i + width])

        # Handle empty text - still need to show cursor
        if not display_lines:
            display_lines = [""]

        # Find which line cursor is on
        cursor_line_idx = self._cursor_pos // width
        cursor_col = self._cursor_pos % width

        # Render each line, with cursor on the appropriate one
        result = []
        for i, line in enumerate(display_lines):
            if i == cursor_line_idx and self.focused:
                # Add cursor to this line
                rendered = self._render_line_with_cursor(line, cursor_col)
                result.append(truncate_to_width(rendered, width))
            else:
                # Plain line (pad to width for consistent display)
                result.append(line)

        # Apply render filters
        for hook_fn in self._render_hooks:
            result = hook_fn(result, width)

        return result

    def _render_line_with_cursor(self, line: str, cursor_col: int) -> str:
        """Render a line with cursor marker at given column."""
        before = line[:cursor_col]
        at = line[cursor_col : cursor_col + 1] or " "
        after = line[cursor_col + 1 :]

        # Get cursor color style
        color_map = {
            "reverse": REVERSE,
            "green": f"{ON_GREEN}{BRIGHT_WHITE}",
            "red": f"{ON_RED}{BRIGHT_WHITE}",
            "blue": f"{ON_BLUE}{BRIGHT_WHITE}",
        }
        cursor_style = color_map.get(self._cursor_color, REVERSE)

        # CURSOR_MARKER for hardware cursor positioning
        return f"{before}{CURSOR_MARKER}{cursor_style}{at}{RESET}{after}"

    def _get_cursor_display_pos(self, width: int) -> tuple[int, int]:
        """Get cursor position in display coordinates.

        With character-based wrapping:
        - line_idx = cursor_pos // width
        - col = cursor_pos % width

        Args:
            width: Display width.

        Returns:
            Tuple of (display_line_index, column_in_that_line).
        """
        if width <= 0:
            return (0, 0)

        line_idx = self._cursor_pos // width
        col = self._cursor_pos % width

        return (line_idx, col)

    def _display_pos_to_absolute(self, line_idx: int, col: int, width: int) -> int:
        """Convert display position to absolute cursor position.

        With character-based wrapping:
        - abs_pos = line_idx * width + col

        Args:
            line_idx: Display line index.
            col: Column in that line.
            width: Display width.

        Returns:
            Absolute character position in text.
        """
        return line_idx * width + col

    def move_cursor_up(self) -> None:
        """Move cursor up by one display line.

        Maintains display column when possible.
        Does nothing if on first display line.
        """
        text = self.get_value()
        width = self._last_width

        if width <= 0 or len(text) <= width:
            return  # Only one line

        cursor_line_idx, cursor_col = self._get_cursor_display_pos(width)

        if cursor_line_idx == 0:
            return  # Already on first line

        # Remember current column for vertical movement
        self._display_column = cursor_col

        # Move to previous line at same column
        prev_line_idx = cursor_line_idx - 1
        prev_line_len = min(width, len(text) - prev_line_idx * width)
        new_col = min(self._display_column, prev_line_len)

        self._cursor_pos = self._display_pos_to_absolute(prev_line_idx, new_col, width)

    def move_cursor_down(self) -> None:
        """Move cursor down by one display line.

        Maintains display column when possible.
        Does nothing if on last display line.
        """
        text = self.get_value()
        width = self._last_width

        if width <= 0 or len(text) <= width:
            return  # Only one line

        cursor_line_idx, cursor_col = self._get_cursor_display_pos(width)
        total_lines = (len(text) + width - 1) // width

        if cursor_line_idx >= total_lines - 1:
            return  # Already on last line

        # Remember current column for vertical movement
        self._display_column = cursor_col

        # Move to next line at same column
        next_line_idx = cursor_line_idx + 1
        next_line_len = min(width, len(text) - next_line_idx * width)
        new_col = min(self._display_column, next_line_len)

        self._cursor_pos = self._display_pos_to_absolute(next_line_idx, new_col, width)

    def _on_submit(self, text: str) -> None:
        """Internal submit handler that forwards to external callback."""
        # CRITICAL: Clear input BEFORE calling on_submit to prevent race condition.
        # pypitui's Input calls on_submit but doesn't clear _text until after.
        # If new terminal input arrives before on_submit returns, it appends to _text.
        # We must clear now so any subsequent input starts fresh.
        self._input.set_value("")
        if self.on_submit:
            self.on_submit(text)

    def handle_input(self, data: str) -> None:
        """Handle keyboard input.

        Args:
            data: Raw input data from terminal.
        """
        # Run input filters first
        for hook_fn in self._input_hooks:
            if hook_fn(data):
                return  # Key was consumed by filter

        # Check for up/down arrows first
        if matches_key(data, Key.up):
            self.move_cursor_up()
            return
        elif matches_key(data, Key.down):
            self.move_cursor_down()
            return
        elif matches_key(data, Key.escape):
            if self.on_cancel:
                self.on_cancel()
            return

        # Update display column on horizontal movement
        if matches_key(data, Key.left) or matches_key(data, Key.right):
            self._input.handle_input(data)
            # Update display column after move
            _, col = self._get_cursor_display_pos(self._last_width)
            self._display_column = col
            return

        # Delegate everything else to wrapped input
        self._input.handle_input(data)

        # Run post-input hooks after value is updated
        for hook_fn in self._post_input_hooks:
            hook_fn()

        # Update display column after typing
        _, col = self._get_cursor_display_pos(self._last_width)
        self._display_column = col
