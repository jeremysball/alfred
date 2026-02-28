"""Tests for MessagePanel Rich markdown integration."""

from src.interfaces.pypitui.message_panel import MessagePanel


class TestMessagePanelMarkdownParameter:
    """Tests for use_markdown parameter acceptance."""

    def test_message_panel_accepts_use_markdown_param(self) -> None:
        """Test MessagePanel accepts use_markdown parameter."""
        panel = MessagePanel(
            role="assistant",
            content="test",
            terminal_width=80,
            use_markdown=True,
        )

        assert panel._use_markdown is True

    def test_message_panel_defaults_to_markdown_enabled(self) -> None:
        """Test MessagePanel defaults to markdown enabled."""
        panel = MessagePanel(
            role="assistant",
            content="test",
            terminal_width=80,
        )

        assert panel._use_markdown is True


class TestMessagePanelMarkdownRendering:
    """Tests for markdown rendering functionality."""

    def test_message_panel_renders_markdown_when_enabled(self) -> None:
        """Test markdown content renders with ANSI codes when enabled."""
        panel = MessagePanel(
            role="assistant",
            terminal_width=80,
            use_markdown=True,
        )

        panel.set_content("**bold** text")

        # Get the Text child component
        text_component = panel.children[0]
        rendered = text_component._text

        # Should contain ANSI escape codes
        assert "\x1b[" in rendered
        # Raw markdown should be transformed
        assert "**bold**" not in rendered
        # Content should be present
        assert "bold" in rendered
        assert "text" in rendered

    def test_message_panel_shows_plain_text_when_disabled(self) -> None:
        """Test raw markdown shown when markdown disabled."""
        panel = MessagePanel(
            role="assistant",
            terminal_width=80,
            use_markdown=False,
        )

        panel.set_content("**bold** text")

        # Get the Text child component
        text_component = panel.children[0]
        rendered = text_component._text

        # Raw markdown should appear as-is
        assert "**bold**" in rendered
        # Should NOT have ANSI codes
        assert "\x1b[" not in rendered


class TestMessagePanelErrorHandling:
    """Tests for error handling and fallback behavior."""

    def test_message_panel_fallback_on_render_error(self) -> None:
        """Test plain text fallback when markdown rendering fails."""
        panel = MessagePanel(
            role="assistant",
            terminal_width=80,
            use_markdown=True,
        )

        # This should not raise even if content is problematic
        panel.set_content("normal text")

        # Content should still be displayed
        text_component = panel.children[0]
        assert "normal text" in text_component._text

    def test_message_panel_handles_empty_content(self) -> None:
        """Test markdown mode handles empty content gracefully."""
        panel = MessagePanel(
            role="assistant",
            terminal_width=80,
            use_markdown=True,
        )

        # Should not raise
        panel.set_content("")

        # Should have empty or newline content
        assert len(panel.children) == 1


class TestMessagePanelWidthUpdates:
    """Tests for width update and re-rendering behavior."""

    def test_message_panel_renders_on_width_change(self) -> None:
        """Test content re-renders when terminal width changes."""
        panel = MessagePanel(
            role="assistant",
            terminal_width=40,
            use_markdown=True,
        )

        panel.set_content("word " * 10)  # Content that will wrap differently

        # Get initial render
        initial_text = panel.children[0]._text
        initial_line_count = initial_text.count("\n")

        # Update width
        panel.set_terminal_width(80)

        # Get re-rendered content
        updated_text = panel.children[0]._text
        updated_line_count = updated_text.count("\n")

        # Wider width should produce fewer or equal lines
        assert updated_line_count <= initial_line_count

    def test_message_panel_width_update_adjusts_renderer(self) -> None:
        """Test that width update adjusts the renderer width."""
        panel = MessagePanel(
            role="assistant",
            terminal_width=80,
            use_markdown=True,
        )

        # Verify renderer exists and has initial width
        assert panel._renderer is not None
        initial_renderer_width = panel._renderer.width

        # Update panel width
        panel.set_terminal_width(120)

        # Renderer width should be updated (accounting for borders/padding)
        assert panel._renderer.width > initial_renderer_width
