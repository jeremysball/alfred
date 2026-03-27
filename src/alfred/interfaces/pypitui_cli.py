"""PyPiTUI-based CLI interface for Alfred.

This module re-exports components from the pypitui subpackage for backwards compatibility.

NOTE: As part of the pypitui v2 migration, many components have been removed or replaced.
The new interface uses pypitui v2 primitives directly. This module will be updated
once the new AlfredTUI implementation is complete.
"""

# Re-export compatibility layer components
from alfred.interfaces.pypitui import (
    CompatTUI,
    HistoryManager,
    OverlayHandle,
    OverlayOptions,
    ProcessTerminal,
    ToastHandler,
    ToastManager,
    ToolCallInfo,
    add_toast,
    format_tokens,
)
from alfred.interfaces.pypitui.commands import (
    Command,
    HealthCommand,
    ListSessionsCommand,
    NewSessionCommand,
    ResumeSessionCommand,
    ShowContextCommand,
    ShowSessionCommand,
    ThrobbersCommand,
)

__all__ = [
    # Compatibility layer
    "CompatTUI",
    "ProcessTerminal",
    "OverlayHandle",
    "OverlayOptions",
    # Commands
    "Command",
    "HealthCommand",
    "ListSessionsCommand",
    "NewSessionCommand",
    "ResumeSessionCommand",
    "ShowContextCommand",
    "ShowSessionCommand",
    "ThrobbersCommand",
    # Components
    "HistoryManager",
    "ToastManager",
    "ToastHandler",
    "ToolCallInfo",
    # Functions
    "add_toast",
    "format_tokens",
]
