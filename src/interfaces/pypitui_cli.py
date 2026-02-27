"""PyPiTUI-based CLI interface for Alfred.

This module re-exports components from the pypitui subpackage for backwards compatibility.
"""

# Re-export everything from the subpackage
from src.interfaces.pypitui import (
    AlfredTUI,
    MessagePanel,
    StatusLine,
    ToolCallInfo,
    ToolCallPanel,
    format_tokens,
)

__all__ = [
    "AlfredTUI",
    "MessagePanel",
    "StatusLine",
    "ToolCallInfo",
    "ToolCallPanel",
    "format_tokens",
]
