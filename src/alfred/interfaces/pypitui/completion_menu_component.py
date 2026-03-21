"""Completion menu as a proper pypitui Component."""

from typing import TYPE_CHECKING

from alfred.interfaces.ansi import RESET, REVERSE
from alfred.interfaces.pypitui.utils import visible_width
from pypitui import Component, Size

if TYPE_CHECKING:
    pass


class CompletionMenuComponent(Component):
    """A dropdown menu component for command completion.

    Renders as a box with completion options and optional descriptions.
    Integrates as a proper Component in the TUI layout.
    """

    @property
    def is_static(self) -> bool:
        """Completion menu is fixed above input and should not scroll."""
        return True

    def __init__(self, max_height: int = 5) -> None:
        """Initialize the completion menu component.

        Args:
            max_height: Maximum number of visible options.
        """
        super().__init__()
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

    @property
    def _options_prop(self) -> list[tuple[str, str | None]]:
        """Access options for selection."""
        return self._options

    def set_options(self, options: list[tuple[str, str | None]]) -> None:
        """Set the menu options and reset selection.

        Args:
            options: List of (value, description) tuples.
        """
        self._options = options
        self._selected_index = 0

    def open(self) -> None:
        """Open the menu."""
        if self._options and not self._is_open:
            self._is_open = True

    def close(self) -> None:
        """Close the menu."""
        if self._is_open:
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

    def measure(self, available_width: int, _available_height: int) -> Size:
        """Measure the menu height for the current option set."""
        return Size(width=available_width, height=len(self.render(available_width)))

    def render(self, width: int) -> list[str]:
        """Render the menu as a list of strings.

        Args:
            width: Total width including box borders.

        Returns:
            List of rendered lines. Returns empty list when closed.
        """
        if width < 3:
            return []

        if not self._is_open or not self._options:
            return []

        visible_options = self._options[: self._max_height]
        lines = []
        inner_width = width - 2

        lines.append("┌" + "─" * inner_width + "┐")
        for i, (value, description) in enumerate(visible_options):
            is_selected = i == self._selected_index
            line = self._render_row(value, description, inner_width, is_selected)
            lines.append("│" + line + "│")
        lines.append("└" + "─" * inner_width + "┘")

        return lines

    def _render_row(
        self,
        value: str,
        description: str | None,
        width: int,
        is_selected: bool,
    ) -> str:
        """Render a single menu row."""
        content_width = width - 2

        if description:
            desc_text = f"  {description}"
            value_space = content_width - visible_width(desc_text)
            if value_space <= 0:
                value_space = content_width
                desc_text = ""
            value_display = (
                value[: max(0, value_space - 1)] + "…"
                if value_space < visible_width(value)
                else value
            )
            # Manual padding since ljust doesn't handle ANSI codes
            padding = max(0, value_space - visible_width(value_display))
            content = f" {value_display}{' ' * padding}{desc_text} "
        else:
            value_display = (
                value[: max(0, content_width - 1)] + "…"
                if visible_width(value) > content_width
                else value
            )
            # Manual padding since ljust doesn't handle ANSI codes
            padding = max(0, content_width - visible_width(value_display))
            content = f" {value_display}{' ' * padding} "

        if is_selected:
            content = f"{REVERSE}{content}{RESET}"

        return content
