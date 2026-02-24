"""Types and enums for live_display module."""

from enum import Enum, auto


class KeyAction(Enum):
    """Actions triggered by keypresses."""

    INSERT = auto()
    INSERT_NEWLINE = auto()  # Shift+Enter for multi-line
    BACKSPACE = auto()
    DELETE = auto()
    DELETE_TO_END = auto()  # Ctrl+K
    DELETE_TO_START = auto()  # Ctrl+U
    DELETE_WORD = auto()  # Ctrl+W
    LEFT = auto()
    RIGHT = auto()
    WORD_LEFT = auto()  # Alt+Left
    WORD_RIGHT = auto()  # Alt+Right
    START = auto()  # Ctrl+I
    END = auto()  # Ctrl+A
    UP = auto()  # History up
    DOWN = auto()  # History down
    TAB = auto()
    SHIFT_TAB = auto()
    ENTER = auto()  # Submit
    SHIFT_ENTER = auto()  # Insert newline (multi-line)
    ESC = auto()
    SUBMIT = auto()
    MOUSE_SCROLL = auto()  # Mouse scroll wheel
