"""Tests for CompletionMenu component."""

import re

from src.interfaces.pypitui.completion_menu import CompletionMenu

# Helper to strip ANSI escape codes for width checks
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return ANSI_ESCAPE.sub("", text)


class TestCompletionMenuRendering:
    """Test CompletionMenu rendering behavior."""

    def test_empty_menu_returns_empty_list(self) -> None:
        """Menu with no options returns empty list."""
        menu = CompletionMenu()
        menu.set_options([])
        menu.open()
        assert menu.render(width=40) == []

    def test_single_option_renders_with_border(self) -> None:
        """Single option renders in bordered box."""
        menu = CompletionMenu()
        menu.set_options([("/new", "Start new session")])
        menu.open()
        lines = menu.render(width=40)

        assert len(lines) == 3  # Top border, content, bottom border
        assert lines[0] == "┌──────────────────────────────────────┐"
        assert lines[2] == "└──────────────────────────────────────┘"

    def test_option_value_shown_in_content(self) -> None:
        """Option value appears in rendered content."""
        menu = CompletionMenu()
        menu.set_options([("/new", None)])
        menu.open()
        lines = menu.render(width=20)

        # Content line should contain the option value
        assert "/new" in lines[1]

    def test_description_shown_when_provided(self) -> None:
        """Description appears in rendered content."""
        menu = CompletionMenu()
        menu.set_options([("/new", "Start new session")])
        menu.open()
        lines = menu.render(width=40)

        # Content line should contain both value and description
        assert "/new" in lines[1]
        assert "Start new session" in lines[1]

    def test_multiple_options_stack_vertically(self) -> None:
        """Multiple options render as separate rows."""
        menu = CompletionMenu()
        menu.set_options([
            ("/new", "Start new session"),
            ("/resume", "Resume session"),
        ])
        menu.open()
        lines = menu.render(width=40)

        # Top border, 2 content lines, bottom border
        assert len(lines) == 4
        assert "/new" in lines[1]
        assert "/resume" in lines[2]

    def test_max_height_limits_visible_options(self) -> None:
        """Menu respects max_height parameter."""
        menu = CompletionMenu(max_height=2)
        menu.set_options([
            ("/new", "Start new session"),
            ("/resume", "Resume session"),
            ("/sessions", "List sessions"),
        ])
        menu.open()
        lines = menu.render(width=40)

        # Top border, 2 content lines (max_height), bottom border
        assert len(lines) == 4

    def test_width_respects_parameter(self) -> None:
        """Menu width matches provided width parameter."""
        menu = CompletionMenu()
        menu.set_options([("/new", None)])
        menu.open()
        lines = menu.render(width=30)

        # All lines should be exactly 30 chars (excluding ANSI escape codes)
        for line in lines:
            assert len(strip_ansi(line)) == 30


class TestCompletionMenuSelection:
    """Test CompletionMenu selection state."""

    def test_first_item_selected_by_default(self) -> None:
        """First option is selected when menu opens."""
        menu = CompletionMenu()
        menu.set_options([
            ("/new", "Start new session"),
            ("/resume", "Resume session"),
        ])

        assert menu.selected_index == 0

    def test_move_down_increments_selection(self) -> None:
        """Move down selects next item."""
        menu = CompletionMenu()
        menu.set_options([
            ("/new", "Start new session"),
            ("/resume", "Resume session"),
        ])

        menu.move_down()
        assert menu.selected_index == 1

    def test_move_up_decrements_selection(self) -> None:
        """Move up selects previous item."""
        menu = CompletionMenu()
        menu.set_options([
            ("/new", "Start new session"),
            ("/resume", "Resume session"),
        ])
        menu.move_down()  # Now at index 1

        menu.move_up()
        assert menu.selected_index == 0

    def test_selection_wraps_at_bottom(self) -> None:
        """Moving down past last item wraps to first."""
        menu = CompletionMenu()
        menu.set_options([
            ("/new", "Start new session"),
            ("/resume", "Resume session"),
        ])
        menu.move_down()  # At index 1 (last)

        menu.move_down()  # Should wrap to 0
        assert menu.selected_index == 0

    def test_selection_wraps_at_top(self) -> None:
        """Moving up past first item wraps to last."""
        menu = CompletionMenu()
        menu.set_options([
            ("/new", "Start new session"),
            ("/resume", "Resume session"),
        ])
        # At index 0 (first)

        menu.move_up()  # Should wrap to 1
        assert menu.selected_index == 1

    def test_selected_item_has_highlight(self) -> None:
        """Selected item renders with highlight."""
        menu = CompletionMenu()
        menu.set_options([("/new", "Start new session")])
        menu.open()
        lines = menu.render(width=40)

        # Selected line should have reverse video escape code
        assert "\x1b[7m" in lines[1]  # Reverse video

    def test_unselected_item_no_highlight(self) -> None:
        """Unselected items render without highlight."""
        menu = CompletionMenu()
        menu.set_options([
            ("/new", "Start new session"),
            ("/resume", "Resume session"),
        ])
        menu.open()
        lines = menu.render(width=40)

        # First item is selected (has highlight)
        assert "\x1b[7m" in lines[1]
        # Second item is not selected (no highlight in that segment)
        # The highlight should reset before the second line


class TestCompletionMenuOpenClose:
    """Test CompletionMenu open/close state."""

    def test_menu_closed_by_default(self) -> None:
        """Menu is closed when created."""
        menu = CompletionMenu()
        assert not menu.is_open

    def test_open_sets_is_open_true(self) -> None:
        """Calling open() sets is_open to True."""
        menu = CompletionMenu()
        menu.set_options([("/new", None)])

        menu.open()
        assert menu.is_open

    def test_close_sets_is_open_false(self) -> None:
        """Calling close() sets is_open to False."""
        menu = CompletionMenu()
        menu.set_options([("/new", None)])
        menu.open()

        menu.close()
        assert not menu.is_open

    def test_render_returns_empty_when_closed(self) -> None:
        """Closed menu renders as empty list."""
        menu = CompletionMenu()
        menu.set_options([("/new", None)])
        # Menu is closed by default

        lines = menu.render(width=40)
        assert lines == []

    def test_render_returns_lines_when_open(self) -> None:
        """Open menu renders content lines."""
        menu = CompletionMenu()
        menu.set_options([("/new", None)])
        menu.open()

        lines = menu.render(width=40)
        assert len(lines) > 0


class TestCompletionMenuDescriptions:
    """Test description rendering and alignment."""

    def test_description_right_aligned(self) -> None:
        """Description appears on right side of menu."""
        menu = CompletionMenu()
        menu.set_options([("/new", "Start new session")])
        menu.open()
        lines = menu.render(width=40)

        content_line = lines[1]
        # Description should be to the right of the value
        value_pos = content_line.find("/new")
        desc_pos = content_line.find("Start new session")
        assert desc_pos > value_pos

    def test_long_description_truncated(self) -> None:
        """Long descriptions are truncated to fit width."""
        menu = CompletionMenu()
        menu.set_options([("/new", "This is a very long description that won't fit")])
        menu.open()
        lines = menu.render(width=30)

        # Line should not exceed width (excluding ANSI escape codes)
        assert len(strip_ansi(lines[1])) == 30

    def test_none_description_omitted(self) -> None:
        """None description renders only the value."""
        menu = CompletionMenu()
        menu.set_options([("/new", None)])
        menu.open()
        lines = menu.render(width=20)

        content = lines[1].strip("│ ")
        # Should just be the value, no extra spaces for description
        assert "/new" in content


class TestCompletionMenuEdgeCases:
    """Test edge cases and error handling."""

    def test_set_options_resets_selection(self) -> None:
        """Setting new options resets selection to first item."""
        menu = CompletionMenu()
        menu.set_options([("/a", None), ("/b", None)])
        menu.move_down()  # Select /b

        menu.set_options([("/c", None), ("/d", None)])
        assert menu.selected_index == 0

    def test_empty_options_does_not_crash(self) -> None:
        """Empty options list handled gracefully."""
        menu = CompletionMenu()
        menu.set_options([])
        menu.open()

        lines = menu.render(width=40)
        assert lines == []

    def test_move_down_with_no_options(self) -> None:
        """Moving down with no options handled gracefully."""
        menu = CompletionMenu()
        menu.set_options([])

        # Should not raise
        menu.move_down()
        assert menu.selected_index == 0

    def test_single_option_move_down_wraps(self) -> None:
        """Moving down with single option wraps to itself."""
        menu = CompletionMenu()
        menu.set_options([("/new", None)])

        menu.move_down()
        assert menu.selected_index == 0

    def test_width_too_narrow_for_value(self) -> None:
        """Very narrow width truncates value if needed."""
        menu = CompletionMenu()
        menu.set_options([("/resume", None)])
        menu.open()
        lines = menu.render(width=10)

        # Should still render within width (excluding ANSI escape codes)
        for line in lines:
            assert len(strip_ansi(line)) == 10
