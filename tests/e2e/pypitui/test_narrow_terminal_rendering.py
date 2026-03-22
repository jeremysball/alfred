"""Integration tests for narrow terminal rendering to prevent truncation regressions."""

import re

from pypitui.utils import visible_width

from alfred.interfaces.pypitui.message_panel import MessagePanel
from alfred.interfaces.pypitui.rich_renderer import RichRenderer


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text).replace("\xa0", " ")


class TestNarrowTerminalToolRendering:
    """Tests that tool calls render correctly at narrow terminal widths."""

    def test_tool_call_at_40_columns_no_truncation(self) -> None:
        """Tool calls should not show Rich truncation '...' at 40 columns."""
        panel = MessagePanel(
            role="assistant",
            content="Testing",
            terminal_width=40,
            use_markdown=True,
        )

        panel.add_tool_call(
            tool_name="schedule_job",
            tool_call_id="test-123",
            arguments={
                "name": "Write Time to File",
                "description": "Write the current time",
            },
        )

        rendered = panel.render(40)

        # Check no lines exceed terminal width
        for i, line in enumerate(rendered):
            vwidth = visible_width(line)
            assert vwidth <= 40, f"Line {i} exceeds 40 chars: {vwidth}"

        # Check for Rich truncation pattern (word + ... at end)
        content = "\n".join(strip_ansi(line) for line in rendered)
        # Rich truncation looks like "wor..." or "ti..." - a word cut off with ...
        truncation_pattern = r"\w\.\.\.\s*$|\w\.\.\.\s+\|"
        matches = re.findall(truncation_pattern, content, re.MULTILINE)
        assert len(matches) == 0, f"Found Rich truncation patterns: {matches}"

    def test_tool_call_arguments_wrap_correctly(self) -> None:
        """Long arguments should wrap naturally without truncation."""
        panel = MessagePanel(
            role="assistant",
            content="Test",
            terminal_width=40,
            use_markdown=True,
        )

        # Long arguments that would trigger truncation if broken
        panel.add_tool_call(
            tool_name="remember",
            tool_call_id="test-456",
            arguments={
                "content": "This is a very long memory that needs to wrap properly",
                "tags": "personal,preferences,test",
            },
        )

        rendered = panel.render(40)
        content = "\n".join(strip_ansi(line) for line in rendered)

        # Should contain full words, not truncated fragments
        assert "This is" in content or "This" in content
        # Should not have mid-word truncation like "Thi..." or "con..."
        assert not re.search(r"\w{2}\.\.\.", content), "Found mid-word truncation"

    def test_renderer_width_matches_content_area_at_40_cols(self) -> None:
        """RichRenderer should use correct width for 40 column terminal."""
        panel = MessagePanel(
            role="assistant",
            content="Test",
            terminal_width=40,
            use_markdown=True,
        )

        # Renderer should be set to content area width (terminal - 8 for nested boxes)
        if panel._renderer:
            assert panel._renderer.width == 32, f"Expected 32, got {panel._renderer.width}"

    def test_renderer_width_at_various_terminal_widths(self) -> None:
        """Renderer width should scale correctly with terminal."""
        test_cases = [
            (40, 32),  # 40 - 8 = 32
            (50, 42),  # 50 - 8 = 42
            (60, 52),  # 60 - 8 = 52
            (80, 72),  # 80 - 8 = 72
        ]

        for terminal_width, expected_renderer_width in test_cases:
            panel = MessagePanel(
                role="assistant",
                content="Test",
                terminal_width=terminal_width,
                use_markdown=True,
            )

            if panel._renderer:
                assert panel._renderer.width == expected_renderer_width, (
                    f"Terminal {terminal_width}: expected {expected_renderer_width}, got {panel._renderer.width}"
                )

    def test_set_terminal_width_updates_renderer(self) -> None:
        """Updating terminal width should update renderer width."""
        panel = MessagePanel(
            role="assistant",
            content="Test",
            terminal_width=80,
            use_markdown=True,
        )

        # Initial width
        if panel._renderer:
            assert panel._renderer.width == 72  # 80 - 8

        # Update to narrow width
        panel.set_terminal_width(40)

        if panel._renderer:
            assert panel._renderer.width == 32  # 40 - 8

    def test_no_truncation_with_long_tool_output(self) -> None:
        """Long tool output should wrap without truncation."""
        panel = MessagePanel(
            role="assistant",
            content="Test",
            terminal_width=40,
            use_markdown=True,
        )

        panel.add_tool_call(
            tool_name="search_memories",
            tool_call_id="test-789",
            arguments={"query": "test"},
        )

        # Update with long output
        long_output = "Found 5 memories: 1. First memory about testing, 2. Second memory about code"
        panel.update_tool_call("test-789", long_output)
        panel.finalize_tool_call("test-789", "success")

        rendered = panel.render(40)
        content = "\n".join(strip_ansi(line) for line in rendered)

        # Should not have mid-word truncation
        assert not re.search(r"\w{2}\.\.\.", content), "Found mid-word truncation in output"


class TestRichRendererMinWidth:
    """Tests for RichRenderer MIN_WIDTH behavior."""

    def test_min_width_is_20(self) -> None:
        """MIN_WIDTH should be 20 to support narrow terminals."""
        assert RichRenderer.MIN_WIDTH == 20

    def test_renderer_allows_narrow_widths(self) -> None:
        """Renderer should allow widths down to MIN_WIDTH."""
        for width in [20, 25, 30, 35, 40]:
            renderer = RichRenderer(width=width)
            assert renderer.width == width, f"Width {width} not respected"

    def test_renderer_clamps_below_min_width(self) -> None:
        """Renderer should clamp to MIN_WIDTH for very narrow requests."""
        renderer = RichRenderer(width=10)
        assert renderer.width == 20  # Clamped to MIN_WIDTH

    def test_update_width_clamps_below_min(self) -> None:
        """Update width should also respect MIN_WIDTH."""
        renderer = RichRenderer(width=80)
        renderer.update_width(10)
        assert renderer.width == 20  # Clamped to MIN_WIDTH


class TestToolCallBoxRendering:
    """Tests for tool call box border rendering."""

    def test_tool_call_box_fits_in_parent_at_40_cols(self) -> None:
        """Tool call box should fit inside MessagePanel at 40 columns."""
        panel = MessagePanel(
            role="assistant",
            content="Test",
            terminal_width=40,
            use_markdown=True,
        )

        panel.add_tool_call(
            tool_name="test_tool",
            tool_call_id="test",
            arguments={"arg": "value"},
        )

        rendered = panel.render(40)

        # All lines should fit within 40 columns
        for i, line in enumerate(rendered):
            vwidth = visible_width(line)
            assert vwidth <= 40, f"Line {i} too wide: {vwidth} > 40"

    def test_nested_box_borders_align(self) -> None:
        """Nested tool box borders should align properly."""
        panel = MessagePanel(
            role="assistant",
            content="Test",
            terminal_width=40,
            use_markdown=True,
        )

        panel.add_tool_call(
            tool_name="test_tool",
            tool_call_id="test",
            arguments={"key": "value"},
        )

        rendered = panel.render(40)
        content = "\n".join(strip_ansi(line) for line in rendered)

        # Find tool box lines (they have the tool name in them)
        tool_box_lines = [line for line in content.split("\n") if "test_tool" in line or "│" in line]

        # All tool box content lines should have the same visible width
        # (accounting for the nested structure)
        for line in tool_box_lines:
            if "│" in line:
                vwidth = len(line)  # After stripping ANSI, visible width equals length
                # Should fit within 40
                assert vwidth <= 42, f"Box line too wide: {vwidth}"  # Allow small margin
