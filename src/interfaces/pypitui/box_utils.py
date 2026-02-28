"""Utilities for building bordered boxes in terminal UI."""

from pypitui.utils import visible_width, wrap_text_with_ansi

from src.interfaces.pypitui.constants import RESET

# Box characters
TOP_LEFT = "┌"
TOP_RIGHT = "┐"
BOTTOM_LEFT = "└"
BOTTOM_RIGHT = "┘"
HORIZONTAL = "─"
VERTICAL = "│"


def build_bordered_box(
    lines: list[str],
    width: int,
    color: str = "",
    title: str | None = None,
    center: bool = True,
) -> list[str]:
    """Build a bordered box with optional title.

    Args:
        lines: Content lines to wrap in box (will be wrapped to fit)
        width: Total box width
        color: ANSI color code (applied to borders)
        title: Optional title for top border
        center: Whether to center content lines

    Returns:
        List of rendered lines with borders
    """
    reset = RESET if color else ""

    # Content width inside borders: │ X + space + content + space + X │
    content_width = max(10, width - 4)

    # Top border
    if title:
        title_part = f"─ {title} "
        dashes_after = width - 2 - len(title_part)
        top = f"{color}{TOP_LEFT}{title_part}{'─' * max(1, dashes_after)}{TOP_RIGHT}{reset}"
    else:
        top = f"{color}{TOP_LEFT}{HORIZONTAL * (width - 2)}{TOP_RIGHT}{reset}"

    result = [top]

    # Wrap and pad content lines
    for line in lines:
        # Wrap long lines to content width
        wrapped = wrap_text_with_ansi(line, content_width) if line else [""]

        for wrapped_line in wrapped:
            if center:
                line_width = visible_width(wrapped_line)
                if line_width < content_width:
                    # Center the text
                    total_padding = content_width - line_width
                    left_pad = total_padding // 2
                    wrapped_line = " " * left_pad + wrapped_line + " " * (total_padding - left_pad)

            content = f" {wrapped_line} "
            result.append(f"{color}{VERTICAL}{reset}{content}{color}{VERTICAL}{reset}")

    # Bottom border
    bottom = f"{color}{BOTTOM_LEFT}{HORIZONTAL * (width - 2)}{BOTTOM_RIGHT}{reset}"
    result.append(bottom)

    return result
