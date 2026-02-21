"""Markdown rendering utility using Rich."""

import os
from io import StringIO

from rich.console import Console
from rich.markdown import Markdown


class MarkdownRenderer:
    """Renders markdown to ANSI codes for terminal display.

    Falls back to raw markdown for non-ANSI terminals.
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize renderer with optional console.

        Args:
            console: Rich Console instance. Creates default if not provided.
        """
        self.console = console if console is not None else Console()

    @property
    def supports_ansi(self) -> bool:
        """Check if terminal supports ANSI codes.

        Returns:
            True if terminal supports ANSI and NO_COLOR is not set.
        """
        if os.environ.get("NO_COLOR"):
            return False
        return bool(self.console.is_terminal)

    def render(self, text: str) -> str:
        """Render markdown text to ANSI string.

        For ANSI terminals, converts markdown to formatted ANSI output.
        For non-ANSI terminals, returns the original markdown text.

        Args:
            text: Markdown text to render.

        Returns:
            Rendered ANSI string or raw markdown.
        """
        if not text:
            return ""

        if not self.supports_ansi:
            return text

        # Create Markdown object and render to string
        md = Markdown(text)

        # Use StringIO to capture rendered output
        string_io = StringIO()
        capture_console = Console(
            file=string_io,
            force_terminal=True,
            width=self.console.width,
            legacy_windows=False,
        )
        capture_console.print(md)

        return string_io.getvalue()
