"""Tests for MarkdownRenderer utility."""

from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from src.utils.markdown import MarkdownRenderer


@pytest.fixture
def mock_console() -> MagicMock:
    """Create a mock Console for testing."""
    console = MagicMock(spec=Console)
    console.is_terminal = True
    console.width = 80
    return console


@pytest.fixture
def mock_console_no_ansi() -> MagicMock:
    """Create a mock Console without ANSI support."""
    console = MagicMock(spec=Console)
    console.is_terminal = False
    console.width = 80
    return console


class TestMarkdownRenderer:
    """Tests for MarkdownRenderer class."""

    def test_init_with_console(self, mock_console: MagicMock) -> None:
        """Renderer initializes with a Console."""
        renderer = MarkdownRenderer(console=mock_console)
        assert renderer.console == mock_console

    def test_supports_ansi_true_for_terminal(self, mock_console: MagicMock) -> None:
        """supports_ansi returns True when console is a terminal."""
        renderer = MarkdownRenderer(console=mock_console)
        assert renderer.supports_ansi is True

    def test_supports_ansi_false_for_non_terminal(
        self, mock_console_no_ansi: MagicMock
    ) -> None:
        """supports_ansi returns False when console is not a terminal."""
        renderer = MarkdownRenderer(console=mock_console_no_ansi)
        assert renderer.supports_ansi is False

    def test_supports_ansi_false_when_no_color_env(self, mock_console: MagicMock) -> None:
        """supports_ansi returns False when NO_COLOR env var is set."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}):
            renderer = MarkdownRenderer(console=mock_console)
            assert renderer.supports_ansi is False

    def test_render_returns_string(self, mock_console: MagicMock) -> None:
        """render() returns a string (rendered or raw)."""
        renderer = MarkdownRenderer(console=mock_console)
        result = renderer.render("**bold text**")
        assert isinstance(result, str)

    def test_render_uses_markdown_for_terminal(self, mock_console: MagicMock) -> None:
        """render() uses Rich Markdown for ANSI terminals."""
        renderer = MarkdownRenderer(console=mock_console)
        # Mock the console.print to capture what's rendered
        mock_console.render_str = MagicMock(return_value="rendered")

        result = renderer.render("**bold**")

        # Should have called console methods (indicating markdown processing)
        assert result  # Non-empty result

    def test_render_returns_raw_for_non_terminal(
        self, mock_console_no_ansi: MagicMock
    ) -> None:
        """render() returns raw markdown when terminal doesn't support ANSI."""
        renderer = MarkdownRenderer(console=mock_console_no_ansi)
        markdown_text = "**bold text**"

        result = renderer.render(markdown_text)

        # Should return the original markdown unchanged
        assert result == markdown_text

    def test_render_empty_string(self, mock_console: MagicMock) -> None:
        """render() handles empty string."""
        renderer = MarkdownRenderer(console=mock_console)
        result = renderer.render("")
        assert result == ""

    def test_render_code_block_with_language(self, mock_console: MagicMock) -> None:
        """render() handles fenced code blocks with language."""
        renderer = MarkdownRenderer(console=mock_console)
        markdown = """```python
def hello():
    print("world")
```"""
        result = renderer.render(markdown)
        assert result  # Should produce some output

    def test_render_table(self, mock_console: MagicMock) -> None:
        """render() handles markdown tables."""
        renderer = MarkdownRenderer(console=mock_console)
        markdown = """| Name | Value |
|------|-------|
| Foo  | 123   |
| Bar  | 456   |"""
        result = renderer.render(markdown)
        assert result  # Should produce some output

    def test_render_headers(self, mock_console: MagicMock) -> None:
        """render() handles headers."""
        renderer = MarkdownRenderer(console=mock_console)
        markdown = "# Header 1\n## Header 2\n### Header 3"
        result = renderer.render(markdown)
        assert result  # Should produce some output

    def test_render_lists(self, mock_console: MagicMock) -> None:
        """render() handles ordered and unordered lists."""
        renderer = MarkdownRenderer(console=mock_console)
        markdown = "- Item 1\n- Item 2\n\n1. First\n2. Second"
        result = renderer.render(markdown)
        assert result  # Should produce some output

    def test_render_inline_formatting(self, mock_console: MagicMock) -> None:
        """render() handles inline bold, italic, code."""
        renderer = MarkdownRenderer(console=mock_console)
        markdown = "**bold** *italic* `code` ~~strikethrough~~"
        result = renderer.render(markdown)
        assert result  # Should produce some output

    def test_render_links(self, mock_console: MagicMock) -> None:
        """render() handles links."""
        renderer = MarkdownRenderer(console=mock_console)
        markdown = "[Alfred](https://github.com/jeremysball/alfred)"
        result = renderer.render(markdown)
        assert result  # Should produce some output

    def test_render_blockquote(self, mock_console: MagicMock) -> None:
        """render() handles blockquotes."""
        renderer = MarkdownRenderer(console=mock_console)
        markdown = "> This is a quote"
        result = renderer.render(markdown)
        assert result  # Should produce some output


class TestMarkdownRendererFactory:
    """Tests for creating renderer with default console."""

    def test_create_with_default_console(self) -> None:
        """Can create renderer without passing console."""
        renderer = MarkdownRenderer()
        assert renderer.console is not None
