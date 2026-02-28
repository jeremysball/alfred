# mypy: disable-error-code="attr-defined, has-type"
"""Patched TUI class that fixes scrollback explosion bug.

The upstream pypitui's _handle_content_growth emits newlines for ALL
scrollback lines on every frame, causing exponential scrollback growth.
This patched version only emits newlines for NEW scrollback lines.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pypitui import TUI

if TYPE_CHECKING:
    from pypitui import Terminal


class PatchedTUI(TUI):
    """TUI subclass that fixes scrollback explosion bug.

    When content exceeds terminal height:
    - Upstream: emits newlines for ALL scrollback lines every frame (bug)
    - Patched: only emits newlines for NEW scrollback lines (correct)
    """

    def __init__(
        self,
        terminal: Terminal,
        show_hardware_cursor: bool = False,
        clear_on_shrink: bool = True,
        anchor_top: bool = False,
    ) -> None:
        super().__init__(
            terminal,
            show_hardware_cursor=show_hardware_cursor,
            clear_on_shrink=clear_on_shrink,
            anchor_top=anchor_top,
        )
        # Track how many scrollback lines we've already emitted
        self._emitted_scrollback_lines: int = 0

    def _handle_content_growth(
        self,
        buffer: str,
        current_count: int,
        previous_count: int,
        term_height: int,
        lines: list[str],
    ) -> str:
        """Handle content growth - only emit newlines for NEW scrollback lines."""
        # When anchor_top is True, skip scrollback handling
        if self._anchor_top:
            return buffer

        if current_count <= term_height or current_count <= previous_count:
            return buffer

        # Calculate how many scrollback lines exist now
        first_visible = current_count - term_height

        # Only emit newlines for NEW scrollback lines (not already emitted)
        new_scrollback_start = self._emitted_scrollback_lines

        if new_scrollback_start >= first_visible:
            # No new scrollback lines to emit
            return buffer

        # Ensure cursor is at bottom of screen
        if self._hardware_cursor_row < term_height - 1:
            buffer += self._move_cursor_relative(term_height - 1)

        # Emit only the NEW scrollback lines
        for i in range(new_scrollback_start, first_visible):
            prev_changed = (
                i >= len(self._previous_lines)
                or self._previous_lines[i] != lines[i]
            )
            if prev_changed:
                buffer += "\r\x1b[2K"
                buffer += lines[i]
            buffer += "\r\n"

        self._hardware_cursor_row = term_height - 1
        self._emitted_scrollback_lines = first_visible

        return buffer

    def invalidate(self) -> None:
        """Reset scrollback tracking on invalidate."""
        super().invalidate()
        self._emitted_scrollback_lines = 0
