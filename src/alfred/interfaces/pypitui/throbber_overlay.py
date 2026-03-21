"""Throbber showcase overlay - displays 9 throbbers at once with pagination."""

import time
from typing import TYPE_CHECKING

from alfred.interfaces.pypitui.throbber import THROBBER_STYLES, Throbber, ThrobberStyle
from pypitui import Component, Size

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
        """Initialize throbbers for current page with consistent animation rate."""
        # Get all style names and split into pages
        all_styles = list(THROBBER_STYLES.keys())
        styles_per_page = 9
        start_idx = self._page * styles_per_page
        end_idx = min(start_idx + styles_per_page, len(all_styles))
        page_styles = all_styles[start_idx:end_idx]

        self._throbbers = []
        for style_name in page_styles:
            original_style = THROBBER_STYLES[style_name]
            # Create custom style with consistent 12fps for fair comparison
            showcase_style = ThrobberStyle(
                name=original_style.name,
                frames=original_style.frames,
                colors=original_style.colors,
                spin_rate=12.0,  # Consistent rate for showcase
                use_bold=original_style.use_bold,
            )
            throbber = Throbber(custom_style=showcase_style)
            self._throbbers.append((original_style.name, throbber))

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

    def measure(self, available_width: int, _available_height: int) -> Size:
        """Measure the throbber showcase overlay."""
        return Size(width=available_width, height=len(self.render(available_width)))

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
        total_pages = (len(THROBBER_STYLES) + 8) // 9
        page_info = f"Page {self._page + 1}/{total_pages}"
        header_text = f" Throbber Showcase ({page_info}) "
        header_pad = max(0, width - 2 - len(header_text))
        left_pad = header_pad // 2
        right_pad = header_pad - left_pad
        lines.append(f"╭{'─' * left_pad}{header_text}{'─' * right_pad}╮")

        # Fixed layout: each cell is exactly 18 chars wide
        # " X name          " = 1 space + 1 throbber + 1 space + 12 char name + 3 spaces padding
        # With borders: │ cell │ cell │ cell │
        # Total: 1 + 18 + 1 + 18 + 1 + 18 + 1 = 58 chars
        cell_width = 18

        # Render in rows of 3
        for i in range(0, len(self._throbbers), 3):
            row = self._throbbers[i : i + 3]

            # Build cells
            cells = []
            for name, throbber in row:
                throbber_str = throbber.render()
                # Strip ANSI for length calculation but preserve it for display
                visible_name = name[:12]
                # Format: " {throbber} {name:12} "
                cell = f" {throbber_str} {visible_name:12} "
                cells.append(cell)

            # Pad to 3 cells
            while len(cells) < 3:
                cells.append(" " * cell_width)

            # Join with vertical borders
            row_content = "│".join(cells)
            lines.append(f"│{row_content}│")

            # Separator between rows (but not after last row)
            if i + 3 < len(self._throbbers):
                # Separator: ├──────┼──────┼──────┤
                sep = "├" + "─" * cell_width + "┼" + "─" * cell_width + "┼" + "─" * cell_width + "┤"
                lines.append(sep[:width])

        # Footer with instructions
        footer_text = " n:next  p:prev  q:quit "
        footer_pad = max(0, width - 2 - len(footer_text))
        left_fpad = footer_pad // 2
        right_fpad = footer_pad - left_fpad
        lines.append(f"╰{'─' * left_fpad}{footer_text}{'─' * right_fpad}╯")

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
