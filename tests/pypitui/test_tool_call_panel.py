"""Tests for ToolCallPanel component."""


class TestToolCallPanel:
    """Tests for ToolCallPanel component (Phase 4.1)."""

    def test_tool_call_panel_shows_tool_name(self):
        """Verify tool name in title."""
        from src.interfaces.pypitui.tool_call_panel import ToolCallPanel

        panel = ToolCallPanel("remember", "call-123")
        assert panel.tool_name == "remember"

    def test_tool_call_panel_running_has_blue_border(self):
        """Verify border contains blue ANSI code when running."""
        from src.interfaces.pypitui.constants import DIM_BLUE
        from src.interfaces.pypitui.tool_call_panel import ToolCallPanel

        panel = ToolCallPanel("bash", "call-1")
        # Border characters should contain the blue color code
        assert DIM_BLUE in panel.HORIZONTAL
        assert DIM_BLUE in panel.VERTICAL

    def test_tool_call_panel_success_has_green_border(self):
        """Verify border contains green ANSI code on success."""
        from src.interfaces.pypitui.constants import DIM_GREEN
        from src.interfaces.pypitui.tool_call_panel import ToolCallPanel

        panel = ToolCallPanel("bash", "call-1")
        panel.set_status("success")
        # Border characters should contain the green color code
        assert DIM_GREEN in panel.HORIZONTAL
        assert DIM_GREEN in panel.VERTICAL

    def test_tool_call_panel_error_has_red_border(self):
        """Verify border contains red ANSI code on error."""
        from src.interfaces.pypitui.constants import DIM_RED
        from src.interfaces.pypitui.tool_call_panel import ToolCallPanel

        panel = ToolCallPanel("bash", "call-1")
        panel.set_status("error")
        # Border characters should contain the red color code
        assert DIM_RED in panel.HORIZONTAL
        assert DIM_RED in panel.VERTICAL

    def test_tool_call_panel_append_output(self):
        """Verify output accumulates."""
        from src.interfaces.pypitui.tool_call_panel import ToolCallPanel

        panel = ToolCallPanel("bash", "call-1")
        panel.append_output("Hello")
        panel.append_output(" World")

        assert panel.output == "Hello World"

    def test_tool_call_panel_truncates_long_output(self):
        """Verify output truncated to MAX_TOOL_OUTPUT chars."""
        from src.interfaces.pypitui.tool_call_panel import (
            MAX_TOOL_OUTPUT,
            ToolCallPanel,
        )

        panel = ToolCallPanel("bash", "call-1")

        # Add more than max
        long_output = "x" * (MAX_TOOL_OUTPUT + 100)
        panel.append_output(long_output)

        assert len(panel.output) == MAX_TOOL_OUTPUT
        # Should keep the end
        assert panel.output.endswith("xxx")

    def test_tool_call_panel_render_contains_output(self):
        """Verify rendered output contains the tool output text."""
        from src.interfaces.pypitui.tool_call_panel import ToolCallPanel

        panel = ToolCallPanel("bash", "call-1")
        panel.append_output("Result: 42")

        lines = panel.render(width=60)
        text = "".join(lines)
        assert "Result: 42" in text
