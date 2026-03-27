"""Rich-based markdown renderer for message content."""

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text


class RichRenderer:
    """Renders markdown content using Rich."""

    MIN_WIDTH = 20

    def __init__(
        self,
        width: int = 80,
        code_theme: str = "monokai",
        justify: str = "left",
    ) -> None:
        """Initialize renderer with specified width.

        Args:
            width: The width for rendering content
            code_theme: Theme for code syntax highlighting
            justify: Text justification (left, center, right, full)
        """
        self.width = max(width, self.MIN_WIDTH)
        self.code_theme = code_theme
        self.justify = justify
        self._console = Console(width=self.width, force_terminal=True)

    def update_width(self, width: int) -> None:
        """Update the rendering width.

        Args:
            width: New width for rendering
        """
        self.width = max(width, self.MIN_WIDTH)
        self._console = Console(width=self.width, force_terminal=True)

    def render_markdown(self, content: str) -> str:
        """Render markdown content to formatted text.

        Args:
            content: Markdown content to render

        Returns:
            Formatted text with ANSI codes
        """
        if not content.strip():
            return ""

        try:
            markdown = Markdown(content, code_theme=self.code_theme)
            with self._console.capture() as capture:
                self._console.print(markdown, soft_wrap=True)
            return capture.get()
        except Exception:
            # Fallback to plain text on error
            return content

    def render_markup(self, content: str) -> str:
        """Render Rich markup to formatted text.

        Args:
            content: Rich markup content (e.g., "[bold]text[/bold]")

        Returns:
            Formatted text with ANSI codes
        """
        if not content:
            return ""

        try:
            with self._console.capture() as capture:
                self._console.print(content, end="", soft_wrap=True)
            return capture.get()
        except Exception:
            # Fallback to plain text on error
            return content

    def render_text(self, content: str) -> str:
        """Render plain text.

        Args:
            content: Plain text content

        Returns:
            Text (potentially wrapped)
        """
        if not content:
            return ""

        text = Text(content)
        with self._console.capture() as capture:
            self._console.print(text, soft_wrap=True)
        return capture.get()
