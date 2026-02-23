"""Inline streaming markdown renderer with prompt_toolkit integration.

Uses manual ANSI cursor control and patch_stdout to render markdown
above a persistent prompt_toolkit prompt without using Rich Live
(which conflicts with prompt_toolkit).
"""

import re
import sys
import time
from dataclasses import dataclass
from typing import Literal

from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.markdown import Markdown

# Minimum time between renders (throttling to prevent flicker)
MIN_RENDER_INTERVAL = 0.05  # 50ms = 20fps max for markdown

# Regex to strip ANSI escape codes for content comparison
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


@dataclass
class RenderSegment:
    """A segment of rendered content (text or tool panel)."""

    type: Literal["text", "tool"]
    content: str
    tool_name: str | None = None
    is_error: bool = False


class StreamingRenderer:
    """Inline streaming markdown renderer with prompt_toolkit integration.

    Renders content inline above a prompt_toolkit prompt using manual
    ANSI cursor control. Uses diff-based updates to only redraw changed lines.

    Usage:
        renderer = StreamingRenderer(console=console)
        renderer.clear()

        async for chunk in llm_stream:
            renderer.add_chunk(chunk)
            renderer.render()

        renderer.finalize()
    """

    def __init__(self, console: Console) -> None:
        """Initialize the renderer.

        Args:
            console: Rich Console instance to use for markdown rendering.
        """
        self.console = console
        self._content_buffer: str = ""
        self._rendered_lines: list[str] = []  # ANSI lines we've drawn
        self._segments: list[RenderSegment] = []
        self._last_render_time: float = 0.0
        self._pending_render: bool = False

    def add_chunk(self, chunk: str) -> None:
        """Add a text chunk to the content buffer.

        Args:
            chunk: Text chunk from LLM stream.
        """
        self._content_buffer += chunk

    def add_tool_panel(
        self,
        tool_name: str,
        result: str,
        is_error: bool = False,
    ) -> None:
        """Add a tool panel segment to the render output.

        Args:
            tool_name: Name of the tool that was called.
            result: Result string from the tool execution.
            is_error: Whether the tool execution resulted in an error.
        """
        # Finalize current text buffer as a segment first
        if self._content_buffer:
            self._segments.append(RenderSegment(type="text", content=self._content_buffer))
            self._content_buffer = ""

        self._segments.append(
            RenderSegment(
                type="tool",
                content=result,
                tool_name=tool_name,
                is_error=is_error,
            )
        )

    def clear(self) -> None:
        """Clear all content and reset renderer state.

        If content was previously rendered, clears it from the terminal.
        """
        # Clear existing rendered content from terminal if any
        if self._rendered_lines:
            with patch_stdout():
                lines_to_move = len(self._rendered_lines)
                if lines_to_move > 0:
                    self._write_ansi(f"\033[{lines_to_move}A")
                for _ in range(lines_to_move):
                    self._write_ansi("\033[K\n")
                if lines_to_move > 0:
                    self._write_ansi(f"\033[{lines_to_move}A")
                sys.stdout.flush()

        self._content_buffer = ""
        self._rendered_lines = []
        self._segments = []
        self._last_render_time = 0.0
        self._pending_render = False

    def render(self, force: bool = False) -> None:
        """Render current content inline, updating only changed lines.

        Args:
            force: If True, render immediately regardless of throttle interval.
                   Use for final renders or explicit updates.
        """
        now = time.time()
        time_since_last = now - self._last_render_time

        # Throttle renders to prevent flicker
        if not force and time_since_last < MIN_RENDER_INTERVAL:
            self._pending_render = True
            return

        self._do_render()
        self._last_render_time = now
        self._pending_render = False

    def flush(self) -> None:
        """Flush any pending render (call after stream completes)."""
        if self._pending_render or self._content_buffer or self._segments:
            self._do_render()
            self._last_render_time = time.time()
            self._pending_render = False

    def _do_render(self) -> None:
        """Render full content, diff against previous, only redraw changed lines."""
        # Render entire content to ANSI
        new_lines = self._render_full()

        # Diff and draw
        self._draw_diff(new_lines)
        self._rendered_lines = new_lines

    def _render_full(self) -> list[str]:
        """Render all content to a list of ANSI-styled lines."""
        lines: list[str] = []

        # Render text segments
        for segment in self._segments:
            if segment.type == "text":
                lines.extend(self._render_markdown(segment.content))

        # Render current buffer content
        if self._content_buffer:
            lines.extend(self._render_markdown(self._content_buffer))

        return lines

    def _diff_changed_indices(self, old: list[str], new: list[str]) -> list[int]:
        """Find indices of lines where TEXT content differs (ignoring ANSI)."""
        changed: list[int] = []
        max_len = max(len(old), len(new))

        for i in range(max_len):
            old_line = old[i] if i < len(old) else ""
            new_line = new[i] if i < len(new) else ""

            # Strip ANSI to compare text only
            old_text = ANSI_ESCAPE.sub("", old_line)
            new_text = ANSI_ESCAPE.sub("", new_line)

            if old_text != new_text:
                changed.append(i)

        return changed

    def _draw_diff(self, new_lines: list[str]) -> None:
        """Draw changed lines using ANSI cursor control."""
        if not new_lines and not self._rendered_lines:
            return

        old_count = len(self._rendered_lines)
        new_count = len(new_lines)

        # Find lines where text changed
        changed = self._diff_changed_indices(self._rendered_lines, new_lines)

        # Case 1: Pure append (all old lines match, only new lines added)
        old_lines_unchanged = not any(i < old_count for i in changed)
        if new_count > old_count and old_lines_unchanged:
            with patch_stdout():
                # Just print new lines - no cursor movement
                for i in range(old_count, new_count):
                    self._write_ansi(f"{new_lines[i]}\033[K\n")
                sys.stdout.flush()
            return

        # Case 2: Some content changed - redraw from first change
        if changed:
            with patch_stdout():
                first_change = min(changed)
                lines_up = old_count - first_change

                if lines_up > 0:
                    self._write_ansi(f"\033[{lines_up}A")

                # Redraw from first change to end
                for i in range(first_change, new_count):
                    self._write_ansi(f"{new_lines[i]}\033[K\n")

                # Clear orphans if shrunk
                orphans = old_count - new_count
                for _ in range(orphans):
                    self._write_ansi("\033[K\n")

                sys.stdout.flush()
            return

    def finalize(self) -> None:
        """Finalize rendering and reset state for next message."""
        self.flush()
        self._content_buffer = ""
        self._segments = []
        self._rendered_lines = []
        self._pending_render = False

    # === Private Methods ===

    def _render_markdown(self, content: str) -> list[str]:
        """Render markdown content to ANSI-styled lines.

        Args:
            content: Markdown text to render.

        Returns:
            List of lines with ANSI escape codes.
        """
        if not content:
            return []

        # Capture rendered markdown to string
        with self.console.capture() as capture:
            self.console.print(Markdown(content))

        output = capture.get()
        return output.splitlines()

    def _write_ansi(self, code: str) -> None:
        """Write ANSI escape code to stdout.

        Args:
            code: ANSI escape code string.
        """
        sys.stdout.write(code)

    @property
    def line_count(self) -> int:
        """Number of lines currently rendered on screen."""
        return len(self._rendered_lines)

    @property
    def has_content(self) -> bool:
        """Whether renderer has any content to display."""
        return bool(self._content_buffer or self._segments)
