"""PyPiTUI components for Alfred CLI."""

# ANSI colors (comprehensive set)
from alfred.interfaces.ansi import (
    BLACK,
    BLUE,
    BOLD,
    BRIGHT_BLACK,
    BRIGHT_BLUE,
    BRIGHT_CYAN,
    BRIGHT_GREEN,
    BRIGHT_MAGENTA,
    BRIGHT_RED,
    BRIGHT_WHITE,
    BRIGHT_YELLOW,
    CYAN,
    DIM,
    GREEN,
    MAGENTA,
    ON_BLACK,
    ON_BLUE,
    ON_BRIGHT_BLACK,
    ON_BRIGHT_BLUE,
    ON_BRIGHT_CYAN,
    ON_BRIGHT_GREEN,
    ON_BRIGHT_MAGENTA,
    ON_BRIGHT_RED,
    ON_BRIGHT_WHITE,
    ON_BRIGHT_YELLOW,
    ON_CYAN,
    ON_GREEN,
    ON_MAGENTA,
    ON_RED,
    ON_WHITE,
    ON_YELLOW,
    RED,
    RESET,
    YELLOW,
)
from alfred.interfaces.pypitui.constants import (
    DIM_BLUE,
    DIM_GREEN,
    DIM_RED,
)
from alfred.interfaces.pypitui.message_panel import MessagePanel
from alfred.interfaces.pypitui.models import ToolCallInfo
from alfred.interfaces.pypitui.status_line import StatusLine
from alfred.interfaces.pypitui.toast import ToastManager, add_toast
from alfred.interfaces.pypitui.toast_overlay import ToastOverlay
from alfred.interfaces.pypitui.tui import AlfredTUI
from alfred.interfaces.pypitui.utils import format_tokens

__all__ = [
    # Classes
    "AlfredTUI",
    "MessagePanel",
    "StatusLine",
    "ToastManager",
    "ToastOverlay",
    "ToolCallInfo",
    # Functions
    "add_toast",
    "format_tokens",
    # ANSI Colors (comprehensive)
    "BLACK",
    "BLUE",
    "BOLD",
    "BRIGHT_BLACK",
    "BRIGHT_BLUE",
    "BRIGHT_CYAN",
    "BRIGHT_GREEN",
    "BRIGHT_MAGENTA",
    "BRIGHT_RED",
    "BRIGHT_WHITE",
    "BRIGHT_YELLOW",
    "CYAN",
    "DIM",
    "GREEN",
    "MAGENTA",
    "ON_BLACK",
    "ON_BLUE",
    "ON_BRIGHT_BLACK",
    "ON_BRIGHT_BLUE",
    "ON_BRIGHT_CYAN",
    "ON_BRIGHT_GREEN",
    "ON_BRIGHT_MAGENTA",
    "ON_BRIGHT_RED",
    "ON_BRIGHT_WHITE",
    "ON_BRIGHT_YELLOW",
    "ON_CYAN",
    "ON_GREEN",
    "ON_MAGENTA",
    "ON_RED",
    "ON_WHITE",
    "ON_YELLOW",
    "RED",
    "RESET",
    "YELLOW",
    # Dim border colors
    "DIM_BLUE",
    "DIM_GREEN",
    "DIM_RED",
]
