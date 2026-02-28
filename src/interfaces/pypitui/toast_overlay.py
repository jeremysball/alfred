"""Toast overlay component for displaying notifications as popups."""

from typing import TYPE_CHECKING

from pypitui import Component
from pypitui.utils import visible_width, wrap_text_with_ansi

from src.interfaces.pypitui.constants import RED, RESET, YELLOW

if TYPE_CHECKING:
    from src.interfaces.pypitui.toast import ToastManager


class ToastOverlay(Component):
    """Overlay component that renders toast notifications as popups.

    This component is designed to be shown as a non-modal overlay at the
    bottom of the screen. It doesn't take focus and auto-dismisses after
    TOAST_DURATION_SECONDS.
    """

    # Box drawing characters
    TOP_LEFT = "┌"
    TOP_RIGHT = "┐"
    BOTTOM_LEFT = "└"
    BOTTOM_RIGHT = "┘"
    HORIZONTAL = "─"
    VERTICAL = "│"

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

        # Content width inside borders (border + space + content + space + border)
        content_width = max(10, width - 4)

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

            # Wrap message to content width
            wrapped_lines = wrap_text_with_ansi(full_message, content_width)

            # Build bordered box
            box_width = content_width + 4  # content + padding + borders
            horiz = self.HORIZONTAL * (box_width - 2)

            # Top border
            lines.append(f"{color}{self.TOP_LEFT}{horiz}{self.TOP_RIGHT}{reset}")

            # Content lines with borders (centered)
            for wrapped_line in wrapped_lines:
                # Pad to content width (centered)
                line_width = visible_width(wrapped_line)
                if line_width < content_width:
                    # Center the text
                    total_padding = content_width - line_width
                    left_pad = total_padding // 2
                    right_pad = total_padding - left_pad
                    wrapped_line = " " * left_pad + wrapped_line + " " * right_pad
                content = f" {wrapped_line} "
                lines.append(f"{color}{self.VERTICAL}{reset}{content}{color}{self.VERTICAL}{reset}")

            # Bottom border
            lines.append(f"{color}{self.BOTTOM_LEFT}{horiz}{self.BOTTOM_RIGHT}{reset}")

        return lines

    def has_toasts(self) -> bool:
        """Check if there are any toasts to display."""
        self._toast_manager.dismiss_expired()
        return len(self._toast_manager.get_all()) > 0
