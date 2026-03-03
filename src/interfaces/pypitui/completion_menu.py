"""Completion menu component for command completion."""

import re

from src.interfaces.ansi import RESET, REVERSE

# ANSI escape pattern for stripping codes
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


class CompletionMenu:
    """A dropdown menu that renders above input for command completion.

    The menu displays a list of completion options with optional descriptions,
    supports selection via up/down navigation, and renders with box-drawing
    characters.
    """

    def __init__(self, max_height: int = 5) -> None:
        """Initialize the completion menu.

        Args:
            max_height: Maximum number of visible options.
        """
        self._max_height = max_height
        self._options: list[tuple[str, str | None]] = []
        self._selected_index = 0
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """Whether the menu is currently open."""
        return self._is_open

    @property
    def selected_index(self) -> int:
        """Current selected option index."""
        return self._selected_index

    def set_options(self, options: list[tuple[str, str | None]]) -> None:
        """Set the menu options and reset selection.

        Args:
            options: List of (value, description) tuples.
        """
        self._options = options
        self._selected_index = 0

    def open(self) -> None:
        """Open the menu."""
        if self._options:
            self._is_open = True

    def close(self) -> None:
        """Close the menu."""
        self._is_open = False

    def move_down(self) -> None:
        """Move selection down, wrapping to top if at bottom."""
        if not self._options:
            return
        self._selected_index = (self._selected_index + 1) % len(self._options)

    def move_up(self) -> None:
        """Move selection up, wrapping to bottom if at top."""
        if not self._options:
            return
        self._selected_index = (self._selected_index - 1) % len(self._options)

    def render(self, width: int) -> list[str]:
        """Render the menu as a list of strings.

        Args:
            width: Total width including box borders.

        Returns:
            List of rendered lines, or empty list if closed or no options.
        """
        if not self._is_open or not self._options or width < 3:
            # Need at least 3 columns for borders + content
            return []

        # Limit visible options to max_height
        visible_options = self._options[: self._max_height]

        lines = []

        # Top border
        inner_width = width - 2  # Account for side borders
        lines.append("┌" + "─" * inner_width + "┐")

        # Content rows
        for i, (value, description) in enumerate(visible_options):
            is_selected = i == self._selected_index
            line = self._render_row(value, description, inner_width, is_selected)
            lines.append("│" + line + "│")

        # Bottom border
        lines.append("└" + "─" * inner_width + "┘")

        return lines

    def _render_row(
        self,
        value: str,
        description: str | None,
        width: int,
        is_selected: bool,
    ) -> str:
        """Render a single menu row.

        Args:
            value: The completion value.
            description: Optional description.
            width: Inner width (excluding borders).
            is_selected: Whether this row is selected.

        Returns:
            Rendered row content.
        """
        # Reserve space for padding
        content_width = width - 2  # Left and right padding

        if description:
            # Value on left, description on right
            # Leave space between them
            desc_text = f"  {description}"
            value_space = content_width - len(desc_text)

            if value_space <= 0:
                # Not enough space for description, drop it and use full width
                value_space = content_width
                desc_text = ""

            if value_space < len(value):
                # Truncate value if too long
                value_display = value[: max(0, value_space - 1)] + "…"
            else:
                value_display = value

            content = f" {value_display:<{max(1, value_space)}}{desc_text} "
        else:
            # Just the value
            if len(value) > content_width:
                value_display = value[: max(0, content_width - 1)] + "…"
            else:
                value_display = value
            content = f" {value_display:<{max(1, content_width)}} "

        # Apply selection highlight (reverse video)
        if is_selected:
            content = f"{REVERSE}{content}{RESET}"

        return content
