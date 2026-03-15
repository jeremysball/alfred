"""Tests for box_utils with wide characters and emojis."""

from pypitui.box_utils import build_bordered_box


class TestBoxUtilsWideChars:
    """Test that box utils handle wide characters correctly."""

    def test_basic_box_no_wide_chars(self):
        """Basic box without wide chars should work."""
        lines = build_bordered_box(
            lines=["Hello", "World"],
            width=20,
        )
        # Should have top border, 2 content lines, bottom border
        assert len(lines) == 4
        # Top border should be full width
        assert len(lines[0]) == 20

    def test_box_with_emoji(self):
        """Box containing emojis should maintain alignment."""
        lines = build_bordered_box(
            lines=["Hello 🐱", "World 🌍"],
            width=30,
        )
        # All lines should be same width
        from pypitui.utils import visible_width

        for line in lines:
            assert visible_width(line) == 30, f"Line '{line}' has wrong width"

    def test_box_with_ansi_colors(self):
        """Box with ANSI colored text should maintain alignment."""
        colored_text = "\x1b[31mRed Text\x1b[0m"
        lines = build_bordered_box(
            lines=[colored_text, "Normal"],
            width=25,
        )
        # All lines should have same visible width
        from pypitui.utils import visible_width

        for line in lines:
            assert visible_width(line) == 25, "Line has wrong visible width"

    def test_box_centered_with_wide_chars(self):
        """Centered content with wide chars should be centered correctly."""
        # "🐱" has width 2, so "Hi 🐱" has visible width 5
        lines = build_bordered_box(
            lines=["Hi 🐱"],
            width=20,
            center=True,
        )
        # Check that content line exists and has correct width
        from pypitui.utils import visible_width

        content_line = lines[1]  # Between top and bottom borders
        assert visible_width(content_line) == 20

    def test_box_with_cjk_chars(self):
        """Box with CJK characters (width 2) should align correctly."""
        lines = build_bordered_box(
            lines=["Hello 中文", "Test"],
            width=30,
        )
        from pypitui.utils import visible_width

        for line in lines:
            assert visible_width(line) == 30

    def test_box_title_with_emoji(self):
        """Box with emoji in title should calculate width correctly."""
        lines = build_bordered_box(
            lines=["Content"],
            width=25,
            title="Box 🎉",
        )
        from pypitui.utils import visible_width

        # Top border with title should be full width
        assert visible_width(lines[0]) == 25


class TestCompletionMenuWideChars:
    """Test completion menu with wide characters."""

    def test_menu_with_ansi_colored_items(self):
        """Menu items with ANSI colors should not overflow."""
        from alfred.interfaces.pypitui.completion_menu_component import (
            CompletionMenuComponent,
        )

        menu = CompletionMenuComponent(max_height=5)
        # Add options with ANSI colors
        colored_value = "\x1b[36m/colored\x1b[0m"
        menu.set_options([(colored_value, "description")])
        menu.open()

        lines = menu.render(width=40)

        # All lines should have consistent visible width
        from pypitui.utils import visible_width

        for line in lines:
            assert visible_width(line) == 40, f"Line '{line[:20]}...' has wrong width"

    def test_menu_truncation_with_wide_chars(self):
        """Long values with wide chars should truncate correctly."""
        from alfred.interfaces.pypitui.completion_menu_component import (
            CompletionMenuComponent,
        )

        menu = CompletionMenuComponent(max_height=5)
        # Long value with emoji (width 2)
        long_value = "a" * 50 + "🐱"
        menu.set_options([(long_value, None)])
        menu.open()

        lines = menu.render(width=30)

        # Value should be truncated, not overflow
        from pypitui.utils import visible_width

        content_line = lines[1]  # First content line
        assert visible_width(content_line) == 30


class TestWrappedInputWideChars:
    """Test wrapped input with wide characters."""

    def test_cursor_position_with_emoji(self):
        """Cursor should be at correct position with emoji in text."""
        from alfred.interfaces.pypitui.wrapped_input import WrappedInput

        inp = WrappedInput()
        inp.set_value("Hello 🐱 World")

        # Set cursor at end
        inp._cursor_pos = len("Hello 🐱 World")  # 14 bytes

        # Render
        lines = inp.render(width=20)

        # Should render without error
        assert len(lines) > 0

    def test_line_wrapping_with_wide_chars(self):
        """Text with wide chars should wrap at correct display positions."""
        from alfred.interfaces.pypitui.wrapped_input import WrappedInput

        inp = WrappedInput()
        # "🐱🐱🐱" has visible width 6, byte length 12
        inp.set_value("🐱🐱🐱abc")

        lines = inp.render(width=8)

        # With width 8, should have 2 lines (6+3 = 9 chars, but width 6 for emojis)
        from pypitui.utils import visible_width

        total_width = sum(visible_width(line) for line in lines)
        # Should cover all content
        assert total_width >= 6  # At least the emojis
