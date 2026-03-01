"""WrappedInput component with display-line navigation.

Wraps pypitui's Input to add up/down arrow navigation across
display lines (handles wrapped text).

Uses character-based wrapping (not word-based) to maintain 1:1
position mapping between text cursor and display position.

Shows ALL display lines at once, with cursor on the appropriate line.
"""

from collections.abc import Callable

from pypitui import CURSOR_MARKER, Component, Focusable, Input, Key, matches_key
from pypitui.utils import truncate_to_width

from src.interfaces.pypitui.completion_addon import CompletionAddon


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

    def __init__(self, placeholder: str = "") -> None:
        """Initialize WrappedInput.

        Args:
            placeholder: Placeholder text when empty and unfocused.
        """
        self._input = Input(placeholder=placeholder)
        self._input.on_submit = self._on_submit
        self._display_column = 0  # Desired column for vertical movement
        self._last_width = 80  # Last render width

        # Callbacks
        self.on_submit: Callable | None = None
        self.on_cancel: Callable | None = None

        # Hook filters for composable behaviors
        self._input_filters: list[Callable[[str], bool]] = []
        self._render_filters: list[Callable[[list[str], int], list[str]]] = []

        # Ghost text providers (for inline completion preview)
        self._ghost_text_providers: list[Callable[[], str | None]] = []

    def add_input_filter(self, filter_fn: Callable[[str], bool]) -> None:
        """Register an input filter.

        Filters are called in order before normal input processing.
        If a filter returns True, the key is consumed and not processed further.

        Args:
            filter_fn: Function taking key string, returning True if consumed.
        """
        self._input_filters.append(filter_fn)

    def add_render_filter(self, filter_fn: Callable[[list[str], int], list[str]]) -> None:
        """Register a render filter.

        Filters are applied in order to transform rendered output lines.

        Args:
            filter_fn: Function taking lines and width, returning modified lines.
        """
        self._render_filters.append(filter_fn)

    def add_ghost_text_provider(self, provider: Callable[[], str | None]) -> None:
        """Add a function that provides ghost text (inline completion preview).

        The ghost text appears dimmed after the cursor position.
        Multiple providers can be added; the first non-None result is used.

        Args:
            provider: Function returning ghost text string, or None if no ghost.
        """
        self._ghost_text_providers.append(provider)

    def with_completion(
        self,
        provider: Callable[[str], list[tuple[str, str | None]]],
        trigger: str = "/",
    ) -> "WrappedInput":
        """Add command completion with fluent API.

        Attaches a CompletionAddon to this input for command completion.
        Returns self for chaining.

        Args:
            provider: Function that takes current text and returns
                     list of (value, description) tuples.
            trigger: Character that triggers completion (default: "/").

        Returns:
            Self for method chaining.

        Example:
            def my_provider(text: str) -> list[tuple[str, str | None]]:
                if text.startswith("/"):
                    return [("/new", "New session"), ("/resume", "Resume")]
                return []

            input_field = WrappedInput().with_completion(my_provider)
        """
        CompletionAddon(self, provider, trigger=trigger)
        return self

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

    def invalidate(self) -> None:
        """Invalidate cache."""
        self._input.invalidate()

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
            for filter_fn in self._render_filters:
                result = filter_fn(result, width)
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
        for filter_fn in self._render_filters:
            result = filter_fn(result, width)

        return result

    def _get_ghost_text(self) -> str | None:
        """Get ghost text from all registered providers.

        Returns:
            First non-None ghost text from providers, or None.
        """
        for provider in self._ghost_text_providers:
            ghost = provider()
            if ghost is not None:
                return ghost
        return None

    def _render_line_with_cursor(self, line: str, cursor_col: int) -> str:
        """Render a line with cursor marker at given column."""
        before = line[:cursor_col]
        at = line[cursor_col : cursor_col + 1] or " "
        after = line[cursor_col + 1 :]

        # Get ghost text (inline completion preview)
        ghost = self._get_ghost_text()
        ghost_rendered = ""
        if ghost:
            # Dim the ghost text using faint ANSI code (\x1b[2m)
            ghost_rendered = f"\x1b[2m{ghost}\x1b[0m"

        # Use reverse video for cursor and emit CURSOR_MARKER for hardware cursor positioning
        return f"{before}{CURSOR_MARKER}\x1b[7m{at}\x1b[27m{after}{ghost_rendered}"

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
        if self.on_submit:
            self.on_submit(text)

    def handle_input(self, data: str) -> None:
        """Handle keyboard input.

        Args:
            data: Raw input data from terminal.
        """
        # Run input filters first
        for filter_fn in self._input_filters:
            if filter_fn(data):
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

        # Update display column after typing
        _, col = self._get_cursor_display_pos(self._last_width)
        self._display_column = col
