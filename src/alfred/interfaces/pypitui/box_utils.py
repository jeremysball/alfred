"""Box drawing utilities for TUI components."""

from alfred.interfaces.ansi import BOLD, RESET


def build_bordered_box(
    lines: list[str],
    width: int,
    color: str,
    title: str = "",
    center: bool = False,
) -> list[str]:
    """Build a bordered box with optional title.

    Args:
        lines: Content lines to display inside the box
        width: Total width of the box (including borders)
        color: ANSI color code for borders
        title: Optional title to display in top border
        center: Whether to center the content

    Returns:
        List of strings representing the box lines
    """
    if width < 10:
        width = 10  # Minimum width

    content_width = width - 4  # Account for "│ " and " │"

    result: list[str] = []

    # Top border with optional title
    if title:
        # Title with bold styling
        title_text = f"{BOLD}{title}{RESET}"
        title_visible_len = len(title)

        # Calculate padding around title
        remaining = content_width - title_visible_len
        if remaining < 0:
            # Title too long, truncate
            title = title[: content_width - 3] + "..."
            title_text = f"{BOLD}{title}{RESET}"
            title_visible_len = len(title)
            remaining = content_width - title_visible_len

        left_pad = remaining // 2
        right_pad = remaining - left_pad

        top = f"{color}┌─{'─' * left_pad}{title_text}{'─' * right_pad}─┐{RESET}"
    else:
        top = f"{color}┌{'─' * (width - 2)}┐{RESET}"

    result.append(top)

    # Content lines
    for line in lines:
        # Truncate or pad content to fit
        if len(line) > content_width:
            content = line[: content_width - 3] + "..."
        else:
            if center:
                padding = content_width - len(line)
                left = padding // 2
                right = padding - left
                content = " " * left + line + " " * right
            else:
                content = line.ljust(content_width)

        result.append(f"{color}│ {RESET}{content}{color} │{RESET}")

    # Bottom border
    bottom = f"{color}└{'─' * (width - 2)}┘{RESET}"
    result.append(bottom)

    return result
