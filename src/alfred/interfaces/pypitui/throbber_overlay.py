"""Throbber showcase overlay - displays 9 throbbers at once with pagination."""

import time
from typing import TYPE_CHECKING

from pypitui import Component

from alfred.interfaces.pypitui.throbber import THROBBER_STYLES, Throbber

if TYPE_CHECKING:
    pass


class ThrobberOverlay(Component):
    """Overlay component that renders multiple throbbers for showcase."""

    def __init__(self, page: int = 0) -> None:
        """Initialize throbber overlay.

        Args:
            page: Page number (0 or 1) to show different sets of throbbers
        """
        super().__init__()
        self._page = page
        self._throbbers: list[tuple[str, Throbber]] = []
        self._last_tick = 0.0
        self._init_throbbers()

    def _init_throbbers(self) -> None:
        """Initialize throbbers for current page."""
        # Get all style names and split into pages
        all_styles = list(THROBBER_STYLES.keys())
        styles_per_page = 9
        start_idx = self._page * styles_per_page
        end_idx = min(start_idx + styles_per_page, len(all_styles))
        page_styles = all_styles[start_idx:end_idx]

        self._throbbers = []
        for style_name in page_styles:
            style = THROBBER_STYLES[style_name]
            throbber = Throbber(style=style_name)
            self._throbbers.append((style.name, throbber))

    def tick(self) -> bool:
        """Advance all throbbers by one frame.

        Returns:
            True if any throbber changed, False otherwise
        """
        changed = False
        now = time.monotonic()
        for _, throbber in self._throbbers:
            if throbber.tick(now):
                changed = True
        return changed

    def render(self, width: int) -> list[str]:
        """Render throbbers in a grid layout.

        Args:
            width: Terminal width

        Returns:
            List of rendered lines
        """
        if not self._throbbers:
            return ["No throbbers to display"]

        lines = []
        # Header
        page_info = f"Page {self._page + 1}/{(len(THROBBER_STYLES) + 8) // 9}"
        lines.append(f"╭─ Throbber Showcase ({page_info}) {'─' * (width - 28)}╮"[:width])

        # Render in rows of 3
        for i in range(0, len(self._throbbers), 3):
            row = self._throbbers[i:i+3]

            # Get rendered throbbers for this row
            cells = []
            for name, throbber in row:
                display = f" {throbber.render()} {name:12} "
                cells.append(display)

            # Join cells with borders
            row_str = "│".join(cells)
            lines.append(f"│{row_str:<{width-2}}│"[:width])

            # Separator line between rows
            if i + 3 < len(self._throbbers):
                lines.append(f"├{'─' * (width-2)}┤"[:width])

        # Footer with instructions
        footer = " n:next p:prev q:quit "
        lines.append(f"╰{footer:─^{width-2}}╯"[:width])

        return lines

    @property
    def page(self) -> int:
        """Current page number."""
        return self._page

    @property
    def max_page(self) -> int:
        """Maximum page number."""
        return (len(THROBBER_STYLES) + 8) // 9 - 1

    def next_page(self) -> bool:
        """Go to next page if available.

        Returns:
            True if page changed, False if at last page
        """
        if self._page < self.max_page:
            self._page += 1
            self._init_throbbers()
            return True
        return False

    def prev_page(self) -> bool:
        """Go to previous page if available.

        Returns:
            True if page changed, False if at first page
        """
        if self._page > 0:
            self._page -= 1
            self._init_throbbers()
            return True
        return False
