"""Tests for WrappedInput component with display-line navigation."""

import re

from alfred.interfaces.pypitui.wrapped_input import WrappedInput


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


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
    """Text wrapping behavior - shows all display lines."""

    def test_wrapped_input_returns_multiple_lines(self) -> None:
        """Long text returns multiple display lines."""
        inp = WrappedInput()
        inp.set_value("hello world this is a long line")
        inp.focused = True

        lines = inp.render(width=10)
        # 31 chars / 10 = 4 lines
        assert len(lines) == 4

    def test_wrapped_input_shows_all_lines(self) -> None:
        """All wrapped lines are visible."""
        inp = WrappedInput()
        inp.set_value("123456789012345678901234567890")
        inp.focused = True

        lines = inp.render(width=10)
        assert len(lines) == 3
        assert strip_ansi(lines[0]) == "1234567890"
        assert strip_ansi(lines[1]) == "1234567890"
        assert strip_ansi(lines[2]) == "1234567890"


class TestWrappedInputCursor:
    """Cursor positioning in wrapped text."""

    def test_wrapped_input_cursor_on_first_line(self) -> None:
        """Cursor at start is on first display line."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(0)
        inp.focused = True

        lines = inp.render(width=5)
        # Cursor (reverse video) should be in first line
        assert "\x1b[7m" in lines[0]

    def test_wrapped_input_cursor_on_second_line(self) -> None:
        """Cursor on second display line has cursor there."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(7)  # Second line (width=5)
        inp.focused = True

        lines = inp.render(width=5)
        # 11 chars at width 5 = 3 lines: "hello", " worl", "d"
        # Cursor at 7 is on line 1 (0-indexed)
        assert "\x1b[7m" in lines[1]
        assert "\x1b[7m" not in lines[0]

    def test_wrapped_input_cursor_on_last_line(self) -> None:
        """Cursor on last display line has cursor there."""
        inp = WrappedInput()
        inp.set_value("hello world")  # 11 chars
        inp.set_cursor_pos(10)  # Last char, last line (width=5)
        inp.focused = True

        lines = inp.render(width=5)
        # Lines: "hello", " worl", "d"
        # Cursor at 10 is on line 2
        assert "\x1b[7m" in lines[2]


class TestWrappedInputNavigation:
    """Arrow key navigation across display lines."""

    def test_wrapped_input_down_moves_to_next_line(self) -> None:
        """Down arrow moves cursor to next display line."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(2)  # On first display line

        inp.render(width=5)
        inp.move_cursor_down()

        # Cursor should have moved to second line (2 -> 7)
        assert inp._cursor_pos == 7

    def test_wrapped_input_up_moves_to_previous_line(self) -> None:
        """Up arrow moves cursor to previous display line."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(8)  # On second display line

        inp.render(width=5)
        inp.move_cursor_up()

        # Cursor should have moved back (8 -> 3)
        assert inp._cursor_pos == 3

    def test_wrapped_input_up_at_top_does_nothing(self) -> None:
        """Up arrow at first line does nothing."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(0)

        inp.render(width=5)
        inp.move_cursor_up()

        assert inp._cursor_pos == 0

    def test_wrapped_input_down_at_bottom_does_nothing(self) -> None:
        """Down arrow at last line does nothing."""
        inp = WrappedInput()
        inp.set_value("hello world")
        inp.set_cursor_pos(11)  # End of text

        inp.render(width=5)
        inp.move_cursor_down()

        assert inp._cursor_pos == 11

    def test_wrapped_input_maintains_column(self) -> None:
        """Vertical movement maintains column position."""
        inp = WrappedInput()
        # Two lines, cursor at column 3 of second line
        inp.set_value("aaaaa bbbbb")
        inp.set_cursor_pos(8)  # Column 3 of "bbbbb"

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
        assert not inp.focused

        inp.focused = True
        assert inp.focused
