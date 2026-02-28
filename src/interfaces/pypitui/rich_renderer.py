"""Rich markdown rendering for PyPiTUI integration."""

from io import StringIO
from typing import Literal

from rich.console import Console
from rich.markdown import Markdown


class RichRenderer:
    """Renders Rich markdown/markup to ANSI text for PyPiTUI display."""

    MIN_WIDTH = 40

    def __init__(
        self,
        width: int = 80,
        code_theme: str = "monokai",
        justify: Literal["left", "center", "right", "full"] = "left",
    ) -> None:
        """Initialize renderer.

        Args:
            width: Terminal width for wrapping
            code_theme: Pygments theme for code blocks
            justify: Text justification
        """
        self.width = max(width, self.MIN_WIDTH)
        self.code_theme = code_theme
        self.justify = justify

    def render_markdown(self, text: str) -> str:
        """Render markdown text to ANSI-colored output.

        Args:
            text: Markdown-formatted text

        Returns:
            ANSI escape sequence formatted text
        """
        try:
            buffer = StringIO()
            console = Console(
                file=buffer,
                width=self.width,
                force_terminal=True,
                color_system="truecolor",
                markup=True,
                emoji=True,
            )

            md = Markdown(
                text,
                code_theme=self.code_theme,
                justify=self.justify,
            )

            console.print(md)
            return buffer.getvalue()
        except Exception:
            return text

    def render_markup(self, text: str) -> str:
        """Render console markup to ANSI-colored output.

        Args:
            text: Text with Rich console markup

        Returns:
            ANSI escape sequence formatted text
        """
        try:
            buffer = StringIO()
            console = Console(
                file=buffer,
                width=self.width,
                force_terminal=True,
                color_system="truecolor",
            )

            console.print(text, markup=True, emoji=True)
            return buffer.getvalue()
        except Exception:
            return text

    def update_width(self, width: int) -> None:
        """Update terminal width.

        Args:
            width: New terminal width
        """
        self.width = max(width, self.MIN_WIDTH)
