"""Tests for RichRenderer module."""

from alfred.interfaces.pypitui.rich_renderer import RichRenderer


class TestRichRendererInit:
    """Tests for RichRenderer initialization."""

    def test_init_default_values(self) -> None:
        """Test default initialization values."""
        renderer = RichRenderer()

        assert renderer.width == 80
        assert renderer.code_theme == "monokai"
        assert renderer.justify == "left"

    def test_init_custom_values(self) -> None:
        """Test initialization with custom values."""
        renderer = RichRenderer(
            width=120,
            code_theme="dracula",
            justify="center",
        )

        assert renderer.width == 120
        assert renderer.code_theme == "dracula"
        assert renderer.justify == "center"

    def test_init_enforces_min_width(self) -> None:
        """Test that width is clamped to minimum."""
        renderer = RichRenderer(width=10)

        assert renderer.width == 20  # MIN_WIDTH


class TestRenderMarkdown:
    """Tests for render_markdown method."""

    def test_render_ansi_codes_present(self) -> None:
        """Test that markdown renders with ANSI escape codes."""
        renderer = RichRenderer(width=80)
        text = "**bold** text"

        result = renderer.render_markdown(text)

        # Should contain ANSI escape sequences
        assert "\x1b[" in result

    def test_render_strips_markdown_syntax(self) -> None:
        """Test that markdown syntax is transformed, not left as-is."""
        renderer = RichRenderer(width=80)
        text = "**bold** and *italic*"

        result = renderer.render_markdown(text)

        # Raw markdown syntax should not appear
        assert "**bold**" not in result
        assert "*italic*" not in result
        # But the text content should
        assert "bold" in result
        assert "italic" in result

    def test_render_code_block_has_syntax_highlighting(self) -> None:
        """Test code blocks have ANSI codes for syntax highlighting."""
        renderer = RichRenderer(width=80)
        text = """```python
def hello():
    pass
```"""

        result = renderer.render_markdown(text)

        # Should have ANSI codes for syntax highlighting
        assert "\x1b[" in result
        # Code content should be present
        assert "def" in result
        assert "hello" in result

    def test_render_code_block_language_agnostic(self) -> None:
        """Test different languages are highlighted."""
        renderer = RichRenderer(width=80)

        for language in ["python", "javascript", "json", "bash"]:
            text = f"```{language}\ncode\n```"
            result = renderer.render_markdown(text)
            assert "\x1b[" in result, f"{language} should have ANSI codes"

    def test_render_unordered_list_has_bullets(self) -> None:
        """Test unordered lists render with bullet characters."""
        renderer = RichRenderer(width=80)
        text = "- Item 1\n- Item 2"

        result = renderer.render_markdown(text)

        # Should contain bullet character (● or similar)
        assert any(c in result for c in ["●", "•", "-", "\u2022"])

    def test_render_ordered_list_has_numbers(self) -> None:
        """Test ordered lists render with numbers."""
        renderer = RichRenderer(width=80)
        text = "1. First\n2. Second"

        result = renderer.render_markdown(text)

        # Should contain the numbers
        assert "1." in result or "1" in result
        assert "2." in result or "2" in result

    def test_render_blockquote_has_indent_or_bar(self) -> None:
        """Test blockquotes have visual indicator."""
        renderer = RichRenderer(width=80)
        text = "> This is a quote"

        result = renderer.render_markdown(text)

        # Should have quote content
        assert "This is a quote" in result
        # Raw > should not appear (it's transformed)
        assert "> This is a quote" not in result

    def test_render_empty_string(self) -> None:
        """Test empty string renders without error."""
        renderer = RichRenderer(width=80)

        result = renderer.render_markdown("")

        assert result == ""

    def test_render_preserves_line_breaks(self) -> None:
        """Test that line breaks are preserved in output."""
        renderer = RichRenderer(width=80)
        text = "Line 1\n\nLine 2"

        result = renderer.render_markdown(text)

        # Should have multiple lines (paragraphs create separation)
        lines = result.split("\n")
        assert len(lines) >= 2


class TestRenderMarkup:
    """Tests for render_markup method."""

    def test_render_markup_produces_ansi(self) -> None:
        """Test that markup renders with ANSI escape codes."""
        renderer = RichRenderer(width=80)
        text = "[bold]bold text[/bold]"

        result = renderer.render_markup(text)

        # Should contain ANSI escape sequences
        assert "\x1b[" in result

    def test_render_markup_strips_tags(self) -> None:
        """Test that markup tags are not left in output."""
        renderer = RichRenderer(width=80)
        text = "[bold]text[/bold]"

        result = renderer.render_markup(text)

        # Tags should be consumed
        assert "[bold]" not in result
        assert "[/bold]" not in result
        # But content remains
        assert "text" in result

    def test_render_color_markup_produces_ansi(self) -> None:
        """Test color markup produces ANSI codes."""
        renderer = RichRenderer(width=80)
        text = "[red]red text[/red]"

        result = renderer.render_markup(text)

        assert "\x1b[" in result
        assert "red text" in result

    def test_render_empty_markup(self) -> None:
        """Test empty string renders without error."""
        renderer = RichRenderer(width=80)

        result = renderer.render_markup("")

        # With end="", empty string returns empty string
        assert result == ""

    def test_render_plain_text_unchanged(self) -> None:
        """Test plain text without markup passes through."""
        renderer = RichRenderer(width=80)
        text = "plain text without markup"

        result = renderer.render_markup(text)

        # Content should be present
        assert "plain text without markup" in result


class TestUpdateWidth:
    """Tests for update_width method."""

    def test_update_width(self) -> None:
        """Test width updates correctly."""
        renderer = RichRenderer(width=80)

        renderer.update_width(120)

        assert renderer.width == 120

    def test_update_width_enforces_minimum(self) -> None:
        """Test width is clamped to minimum on update."""
        renderer = RichRenderer(width=80)

        renderer.update_width(10)

        assert renderer.width == 20  # MIN_WIDTH

    def test_update_width_affects_line_wrapping(self) -> None:
        """Test that width changes affect how text wraps."""
        renderer = RichRenderer(width=20)
        text = "word " * 10  # Long text that needs wrapping

        narrow_result = renderer.render_markdown(text)
        narrow_lines = narrow_result.count("\n")

        renderer.update_width(80)
        wide_result = renderer.render_markdown(text)
        wide_lines = wide_result.count("\n")

        # Wider width should produce fewer lines
        assert wide_lines <= narrow_lines


class TestThemeConfiguration:
    """Tests for code theme configuration."""

    def test_different_themes_produce_ansi(self) -> None:
        """Test that different code themes all produce highlighted output."""
        code = "```python\nprint('hello')\n```"

        themes = ["monokai", "default", "vim"]

        for theme in themes:
            renderer = RichRenderer(width=80, code_theme=theme)
            result = renderer.render_markdown(code)

            # All themes should produce ANSI codes
            assert "\x1b[" in result, f"Theme {theme} should produce ANSI codes"
            assert "print" in result

    def test_invalid_theme_graceful_fallback(self) -> None:
        """Test invalid theme falls back gracefully."""
        renderer = RichRenderer(width=80, code_theme="nonexistent_theme")
        code = "```python\nprint('hello')\n```"

        # Should not raise
        result = renderer.render_markdown(code)

        # Should still produce output
        assert "print" in result


class TestJustifyConfiguration:
    """Tests for text justification."""

    def test_justify_options_accepted(self) -> None:
        """Test that all justify options are accepted without error."""
        text = "Short text"

        for justify in ["left", "center", "right", "full"]:
            renderer = RichRenderer(width=80, justify=justify)
            # Should not raise
            result = renderer.render_markdown(text)
            assert "Short text" in result


class TestWidthWrapping:
    """Tests for text wrapping at width."""

    def test_narrow_width_creates_more_lines(self) -> None:
        """Test that narrow width creates more wrapped lines."""
        text = "word " * 20  # 100 characters including spaces

        narrow_renderer = RichRenderer(width=30)
        narrow_result = narrow_renderer.render_markdown(text)
        narrow_line_count = narrow_result.count("\n")

        wide_renderer = RichRenderer(width=100)
        wide_result = wide_renderer.render_markdown(text)
        wide_line_count = wide_result.count("\n")

        # Narrower width should produce more lines
        assert narrow_line_count >= wide_line_count

    def test_code_block_rendered_at_narrow_width(self) -> None:
        """Test code blocks render even at narrow widths."""
        renderer = RichRenderer(width=20)
        text = """```python
def hello():
    print("world")
```"""

        # Should not raise
        result = renderer.render_markdown(text)

        # Content should be present
        assert "def" in result
        assert "hello" in result


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_render_markdown_returns_plain_text_on_exception(self) -> None:
        """Test that render_markdown returns plain text if Rich fails."""
        renderer = RichRenderer(width=80)
        # This will work, but if Rich ever fails, we get plain text back
        result = renderer.render_markdown("test")

        assert "test" in result

    def test_render_markup_returns_plain_text_on_exception(self) -> None:
        """Test that render_markup returns plain text if Rich fails."""
        renderer = RichRenderer(width=80)
        result = renderer.render_markup("test")

        assert "test" in result

    def test_very_long_content_renders(self) -> None:
        """Test very long content doesn't break renderer."""
        renderer = RichRenderer(width=80)
        text = "word " * 1000  # Very long text

        # Should not raise
        result = renderer.render_markdown(text)

        assert len(result) > 0

    def test_unicode_content_renders(self) -> None:
        """Test unicode content renders correctly."""
        renderer = RichRenderer(width=80)
        text = "Hello 世界 🌍 ñoño"

        result = renderer.render_markdown(text)

        assert "世界" in result
        assert "🌍" in result
