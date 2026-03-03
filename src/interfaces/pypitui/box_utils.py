"""Utilities for building bordered boxes in terminal UI."""

from pypitui.utils import visible_width, wrap_text_with_ansi

from src.interfaces.ansi import RESET

# Box characters
TOP_LEFT = "┌"
TOP_RIGHT = "┐"
BOTTOM_LEFT = "└"
BOTTOM_RIGHT = "┘"
HORIZONTAL = "─"
VERTICAL = "│"
# Non-breaking space to prevent word-wrapping from splitting border lines
NBSP = "\u00a0"


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

    # Top border - use non-breaking spaces to prevent word-wrapping
    if title:
        # ┌─ title ──────┐  (spaces are non-breaking to prevent wrap splitting)
        title_part = f"─{NBSP}{title}{NBSP}"
        title_visible = visible_width(title) + 3  # ─ + nbsp + title + nbsp
        dashes_after = width - 2 - title_visible  # -2 for TOP_LEFT and TOP_RIGHT
        top = f"{color}{TOP_LEFT}{title_part}{'─' * max(1, dashes_after)}{TOP_RIGHT}{reset}"
    else:
        top = f"{color}{TOP_LEFT}{HORIZONTAL * (width - 2)}{TOP_RIGHT}{reset}"

    result = [top]

    # Wrap and pad content lines
    for line in lines:
        # Wrap long lines to content width
        wrapped = wrap_text_with_ansi(line, content_width) if line else [""]

        for wrapped_line in wrapped:
            line_width = visible_width(wrapped_line)
            if line_width < content_width:
                if center:
                    # Center the text using NBSP to prevent word-wrapping
                    total_padding = content_width - line_width
                    left_pad = total_padding // 2
                    right_pad = total_padding - left_pad
                    wrapped_line = NBSP * left_pad + wrapped_line + NBSP * right_pad
                else:
                    # Left-align: pad with NBSP on right to prevent word-wrapping
                    wrapped_line = wrapped_line + NBSP * (content_width - line_width)

            # Use NBSP around content to prevent wrap splitting
            content = f"{NBSP}{wrapped_line}{NBSP}"
            result.append(f"{color}{VERTICAL}{reset}{content}{color}{VERTICAL}{reset}")

    # Bottom border
    bottom = f"{color}{BOTTOM_LEFT}{HORIZONTAL * (width - 2)}{BOTTOM_RIGHT}{reset}"
    result.append(bottom)

    return result
