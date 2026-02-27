"""WrappedInput component with display-line navigation.

Wraps pypitui's Input to add up/down arrow navigation across
display lines (handles wrapped text).

Uses character-based wrapping (not word-based) to maintain 1:1
position mapping between text cursor and display position.
"""

from collections.abc import Callable

from pypitui import Component, Focusable, Input, Key, matches_key
from pypitui.utils import truncate_to_width


class WrappedInput(Component, Focusable):
    """Text input with display-line navigation for wrapped text.

    Wraps pypitui's Input component and adds:
    - Up/down arrow navigation across wrapped display lines
    - Maintains display column during vertical movement
    - Proper cursor positioning in wrapped text

    Uses character-based wrapping (not word-based) for reliable
    position mapping.

    Usage:
        inp = WrappedInput(placeholder="Type here...")
        inp.on_submit = lambda text: print(f"Submitted: {text}")

        # In render loop:
        lines = inp.render(width=80)
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
        """Render input showing only the current display line.

        Args:
            width: Terminal width in columns.

        Returns:
            Single-element list containing the display line with cursor.
        """
        self._last_width = width
        text = self.get_value()

        if not text and not self.focused:
            # Show placeholder
            return self._input.render(width)

        if width <= 0:
            return [text] if text else [""]

        # Get which display line the cursor is on
        cursor_line_idx = self._cursor_pos // width

        # Extract just that line's text
        line_start = cursor_line_idx * width
        line_end = min(line_start + width, len(text))
        line_text = text[line_start:line_end]

        # Cursor position within this line
        cursor_col = self._cursor_pos % width

        # Render with cursor
        if self.focused:
            rendered = self._render_line_with_cursor(line_text, cursor_col)
            # Truncate to fit width exactly (cursor markers are 0-width in visible terms)
            return [truncate_to_width(rendered, width)]
        else:
            return [line_text] if line_text else [" "]

    def _render_line_with_cursor(self, line: str, cursor_col: int) -> str:
        """Render a line with cursor marker at given column."""
        before = line[:cursor_col]
        at = line[cursor_col : cursor_col + 1] or " "
        after = line[cursor_col + 1 :]

        # Use reverse video for cursor (no extra visible char)
        return f"{before}\x1b[7m{at}\x1b[27m{after}"

    def _get_display_lines(self, text: str, width: int) -> list[str]:
        """Get display lines with character-based wrapping.

        Simple character-based wrapping maintains 1:1 position mapping:
        - Position 0-9 → line 0
        - Position 10-19 → line 1
        - etc.

        Args:
            text: Text to wrap.
            width: Maximum line width.

        Returns:
            List of display lines.
        """
        if width <= 0 or not text:
            return [text] if text else [""]

        lines = []
        for i in range(0, len(text), width):
            lines.append(text[i : i + width])

        return lines if lines else [""]

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
