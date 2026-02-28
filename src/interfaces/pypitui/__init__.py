"""PyPiTUI components for Alfred CLI."""

from src.interfaces.pypitui.constants import (
    CYAN,
    DIM,
    DIM_BLUE,
    DIM_GREEN,
    DIM_RED,
    GREEN,
    MAX_TOOL_OUTPUT,
    RED,
    RESET,
    YELLOW,
)
from src.interfaces.pypitui.message_panel import MessagePanel
from src.interfaces.pypitui.models import ToolCallInfo
from src.interfaces.pypitui.status_line import StatusLine
from src.interfaces.pypitui.toast import ToastManager, add_toast
from src.interfaces.pypitui.toast_overlay import ToastOverlay
from src.interfaces.pypitui.tui import AlfredTUI
from src.interfaces.pypitui.utils import format_tokens

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
    # Constants
    "CYAN",
    "DIM",
    "DIM_BLUE",
    "DIM_GREEN",
    "DIM_RED",
    "GREEN",
    "MAX_TOOL_OUTPUT",
    "RED",
    "RESET",
    "YELLOW",
]
