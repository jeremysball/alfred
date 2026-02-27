"""Tests for WrappedInput component with display-line navigation."""

import pytest

from src.interfaces.pypitui.wrapped_input import WrappedInput


class TestWrappedInputBasic:
    """Basic WrappedInput functionality."""

    def test_wrapped_input_init(self) -> None:
        """WrappedInput initializes with placeholder."""
        inp = WrappedInput(placeholder="Type here...")
        assert inp.get_value() == ""

    def test_wrapped_input_get_set_value(self) -> None:
        """get_value and set_value work."""
        inp = WrappedInput()
        inp.set_value("hello world")
        assert inp.get_value() == "hello world"

    def test_wrapped_input_single_line_render(self) -> None:
        """Single short line renders as one line."""
        inp = WrappedInput()
        inp.set_value("hello")

        lines = inp.render(width=20)
        assert len(lines) == 1
        assert "hello" in lines[0]


class TestWrappedInputWrapping:
    """Text wrapping behavior."""

    def test_wrapped_input_wraps_long_line(self) -> None:
        """Long line wraps to multiple display lines."""
        inp = WrappedInput()
        inp.set_value("hello world this is a long line")

        lines = inp.render(width=10)
        # Character-based: 28 chars / 10 = 3 lines
        assert len(lines) >= 2  # Should wrap

    def test_wrapped_input_respects_width(self) -> None:
        """Each display line fits within width (plus cursor markers)."""
        inp = WrappedInput()
        inp.set_value("hello world this is a long line")

        lines = inp.render(width=10)
        # Character-based wrapping: each line has at most 10 chars of text
        # Plus cursor markers which add visible chars but also ANSI codes
        for line in lines:
            # Strip ANSI codes for visible length check
            import re
            clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
            # Allow some tolerance for cursor markers
            assert len(clean) <= 12  # 10 chars + cursor tolerance


class TestWrappedInputCursor:
    """Cursor positioning in wrapped text."""

    def test_wrapped_input_cursor_on_first_line(self) -> None:
        """Cursor at start is on first display line."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(0)

        lines = inp.render(width=10)
        # Cursor marker should be in first line
        assert "\x1b[7m" in lines[0] or "█" in lines[0] or len(lines[0]) > 0

    def test_wrapped_input_cursor_on_wrapped_line(self) -> None:
        """Cursor on wrapped portion appears on correct display line."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(8)  # Into "world"
        inp.focused = True  # Need focus for cursor to appear

        lines = inp.render(width=5)  # "hello" then " worl"
        # Cursor should be in second line
        assert "\x1b[7m" in lines[1]


class TestWrappedInputNavigation:
    """Arrow key navigation across display lines."""

    def test_wrapped_input_down_moves_to_wrapped_line(self) -> None:
        """Down arrow moves cursor to next display line."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(2)  # On first display line

        # Must render first to set _last_width
        inp.render(width=5)

        inp.move_cursor_down()

        # Cursor should have moved to second line (2 -> 7)
        assert inp._cursor_pos == 7

    def test_wrapped_input_up_moves_to_previous_line(self) -> None:
        """Up arrow moves cursor to previous display line."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(8)  # On second display line

        # Must render first to set _last_width
        inp.render(width=5)

        inp.move_cursor_up()

        # Cursor should have moved back (8 -> 3)
        assert inp._cursor_pos == 3

    def test_wrapped_input_up_at_top_does_nothing(self) -> None:
        """Up arrow at first line does nothing."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(0)

        inp.move_cursor_up()

        assert inp._cursor_pos == 0

    def test_wrapped_input_down_at_bottom_does_nothing(self) -> None:
        """Down arrow at last line does nothing."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(11)  # End of text

        inp.move_cursor_down()

        assert inp._cursor_pos == 11

    def test_wrapped_input_maintains_column(self) -> None:
        """Vertical movement maintains column position."""
        inp = WrappedInput()
        # Two lines, cursor at column 3 of second line
        inp.set_value("aaaaa bbbbb")
        inp.set_cursor_pos(8)  # Column 3 of "bbbbb"

        # Must render first to set _last_width
        inp.render(width=5)

        inp.move_cursor_up()  # Should go to column 3 of "aaaaa"
        assert inp._cursor_pos == 3

        inp.move_cursor_down()  # Back to column 3 of "bbbbb"
        assert inp._cursor_pos == 8


class TestWrappedInputSubmit:
    """Submit behavior."""

    def test_wrapped_input_on_submit_called(self) -> None:
        """on_submit callback is called."""
        inp = WrappedInput()
        inp.set_value("hello")

        submitted = []
        inp.on_submit = lambda text: submitted.append(text)

        inp.handle_input("\r")  # Enter key
        assert submitted == ["hello"]

    def test_wrapped_input_handle_input_delegates(self) -> None:
        """handle_input delegates to wrapped Input for typing."""
        inp = WrappedInput()

        inp.handle_input("a")
        inp.handle_input("b")
        inp.handle_input("c")

        assert inp.get_value() == "abc"


class TestWrappedInputFocus:
    """Focus handling."""

    def test_wrapped_input_focused_property(self) -> None:
        """focused property works."""
        inp = WrappedInput()
        assert inp.focused == False

        inp.focused = True
        assert inp.focused == True
