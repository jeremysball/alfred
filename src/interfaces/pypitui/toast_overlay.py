"""Toast overlay component for displaying notifications as popups."""

from typing import TYPE_CHECKING

from pypitui import Component

from src.interfaces.ansi import RED, RESET, YELLOW
from src.interfaces.pypitui.box_utils import build_bordered_box

if TYPE_CHECKING:
    from src.interfaces.pypitui.toast import ToastManager


class ToastOverlay(Component):
    """Overlay component that renders toast notifications as popups.

    This component is designed to be shown as a non-modal overlay at the
    bottom of the screen. It doesn't take focus and auto-dismisses after
    TOAST_DURATION_SECONDS.
    """

    def __init__(self, toast_manager: "ToastManager") -> None:
        """Initialize the toast overlay.

        Args:
            toast_manager: The ToastManager to render toasts from
        """
        self._toast_manager = toast_manager

    def invalidate(self) -> None:
        """Mark component as needing re-render (no-op)."""
        pass

    def render(self, width: int) -> list[str]:
        """Render current toasts as bordered overlay lines.

        Args:
            width: Available width for rendering

        Returns:
            List of rendered lines with borders
        """
        # Clean up expired toasts first
        self._toast_manager.dismiss_expired()

        toasts = self._toast_manager.get_all()
        if not toasts:
            return []

        # Use most of the terminal width for the box
        box_width = max(20, width - 4)

        lines = []
        for toast in toasts:
            # Color based on level
            if toast.level == "error":
                color = RED
            elif toast.level == "warning":
                color = YELLOW
            else:
                color = ""
            reset = RESET if color else ""

            # Format: [LEVEL] message
            prefix = f"{color}[{toast.level.upper()}]{reset}"
            full_message = f"{prefix} {toast.message}"

            # Build bordered box using utility
            box_lines = build_bordered_box(
                lines=[full_message],
                width=box_width,
                color=color,
                center=True,
            )
            lines.extend(box_lines)

        return lines

    def has_toasts(self) -> bool:
        """Check if there are any toasts to display."""
        self._toast_manager.dismiss_expired()
        return len(self._toast_manager.get_all()) > 0
