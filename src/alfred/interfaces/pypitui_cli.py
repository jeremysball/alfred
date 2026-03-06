"""PyPiTUI-based CLI interface for Alfred.

This module re-exports components from the pypitui subpackage for backwards compatibility.
"""

# Re-export everything from the subpackage
from alfred.interfaces.pypitui import (
    AlfredTUI,
    MessagePanel,
    StatusLine,
    ToastManager,
    ToastOverlay,
    ToolCallInfo,
    add_toast,
    format_tokens,
)

__all__ = [
    "AlfredTUI",
    "MessagePanel",
    "StatusLine",
    "ToastManager",
    "ToastOverlay",
    "ToolCallInfo",
    "add_toast",
    "format_tokens",
]
