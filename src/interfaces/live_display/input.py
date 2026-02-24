"""Input handling for LiveDisplay."""

import re
from readchar import readkey
from rich.text import Text

from src.theme import Theme

# readchar.key constants - mypy doesn't have stubs
# ruff: noqa
from readchar.key import (  # type: ignore[attr-defined]
    BACKSPACE,
    DELETE,
    DOWN,
    ENTER,
    ESC,
    LEFT,
    RIGHT,
    SHIFT_TAB,
    TAB,
    UP,
)

from .types import KeyAction as KeyAction


# Mouse action codes (SGR extended mode)
MOUSE_SCROLL_UP = 64
MOUSE_SCROLL_DOWN = 65

# Regex to parse SGR mouse events: \x1b[<action;col;rowM or m
MOUSE_EVENT_RE = re.compile(r'\x1b\[<(\d+);(\d+);(\d+)([Mm])')


class InputReader:
    """Read keyboard input and translate to actions."""

    def read(self) -> tuple[KeyAction, str]:
        """Read a keypress and return (action, char).
        
        Also handles mouse scroll events, returning MOUSE_SCROLL action
        with 'up' or 'down' as the char.
        """
        key = readkey()

        # Check for mouse scroll events (SGR format: \x1b[<64;col;rowM for scroll up)
        if key == '\x1b':
            # Might be start of mouse event, read more
            # Note: readkey should have read the full sequence, check if it matches
            pass
        
        # Try to match mouse event in the key
        mouse_match = MOUSE_EVENT_RE.match(key)
        if mouse_match:
            action = int(mouse_match.group(1))
            if action == MOUSE_SCROLL_UP:
                return (KeyAction.MOUSE_SCROLL, "up")
            elif action == MOUSE_SCROLL_DOWN:
                return (KeyAction.MOUSE_SCROLL, "down")
            # Other mouse events, ignore
            return (KeyAction.ESC, "")

        if key == BACKSPACE:
            return (KeyAction.BACKSPACE, "")
        elif key == DELETE:
            return (KeyAction.DELETE, "")
        elif key == LEFT:
            return (KeyAction.LEFT, "")
        elif key == RIGHT:
            return (KeyAction.RIGHT, "")
        elif key == UP:
            return (KeyAction.UP, "")
        elif key == DOWN:
            return (KeyAction.DOWN, "")
        elif key == ENTER:
            return (KeyAction.ENTER, "")
        elif key == "\x1b[13;2u" or key == "\x1b[13;2~":  # Shift+Enter
            return (KeyAction.SHIFT_ENTER, "")
        elif key == ESC:
            return (KeyAction.ESC, "")
        elif key == TAB:
            return (KeyAction.TAB, "")
        elif key == SHIFT_TAB:
            return (KeyAction.SHIFT_TAB, "")
        elif key == "\x01":  # Ctrl+A
            return (KeyAction.END, "")
        elif key == "\x09":  # Ctrl+I
            return (KeyAction.TAB, "")
        elif key == "\x0b":  # Ctrl+K
            return (KeyAction.DELETE_TO_END, "")
        elif key == "\x15":  # Ctrl+U
            return (KeyAction.DELETE_TO_START, "")
        elif key == "\x17":  # Ctrl+W
            return (KeyAction.DELETE_WORD, "")
        elif key.startswith("\x1b") and len(key) > 1:
            rest = key[1:]
            if rest == "b":  # Alt+B
                return (KeyAction.WORD_LEFT, "")
            elif rest == "f":  # Alt+F
                return (KeyAction.WORD_RIGHT, "")
            elif rest == "[1;3D":  # Alt+Left
                return (KeyAction.WORD_LEFT, "")
            elif rest == "[1;3C":  # Alt+Right
                return (KeyAction.WORD_RIGHT, "")
            elif rest == "[1;5D":  # Ctrl+Left
                return (KeyAction.WORD_LEFT, "")
            elif rest == "[1;5C":  # Ctrl+Right
                return (KeyAction.WORD_RIGHT, "")
            return (KeyAction.ESC, "")

        if key.isprintable():
            return (KeyAction.INSERT, key)

        return (KeyAction.ESC, "")


class PromptInput:
    """Custom input buffer with cursor tracking."""

    def __init__(self) -> None:
        self.buffer: str = ""
        self.cursor: int = 0

    def insert(self, char: str) -> None:
        """Insert character at cursor position."""
        self.buffer = self.buffer[: self.cursor] + char + self.buffer[self.cursor :]
        self.cursor += len(char)

    def delete_left(self) -> None:
        """Delete character before cursor (Backspace)."""
        if self.cursor > 0:
            self.buffer = self.buffer[: self.cursor - 1] + self.buffer[self.cursor :]
            self.cursor -= 1

    def delete_right(self) -> None:
        """Delete character at cursor (Delete key)."""
        if self.cursor < len(self.buffer):
            self.buffer = self.buffer[: self.cursor] + self.buffer[self.cursor + 1 :]

    def delete_to_end(self) -> None:
        """Delete from cursor to end of line (Ctrl+K)."""
        self.buffer = self.buffer[: self.cursor]

    def delete_to_start(self) -> None:
        """Delete from start to cursor (Ctrl+U)."""
        self.buffer = self.buffer[self.cursor :]
        self.cursor = 0

    def delete_word(self) -> None:
        """Delete word before cursor (Ctrl+W)."""
        pos = self.cursor - 1
        while pos >= 0 and self.buffer[pos] == " ":
            pos -= 1
        while pos >= 0 and self.buffer[pos] != " ":
            pos -= 1
        word_start = pos + 1
        self.buffer = self.buffer[:word_start] + self.buffer[self.cursor :]
        self.cursor = word_start

    def move_left(self) -> None:
        """Move cursor left one character."""
        if self.cursor > 0:
            self.cursor -= 1

    def move_right(self) -> None:
        """Move cursor right one character."""
        if self.cursor < len(self.buffer):
            self.cursor += 1

    def move_word_left(self) -> None:
        """Move cursor left one word (Alt+Left)."""
        pos = self.cursor - 1
        while pos >= 0 and self.buffer[pos] == " ":
            pos -= 1
        while pos >= 0 and self.buffer[pos] != " ":
            pos -= 1
        self.cursor = max(0, pos + 1)

    def move_word_right(self) -> None:
        """Move cursor right one word (Alt+Right)."""
        pos = self.cursor
        while pos < len(self.buffer) and self.buffer[pos] == " ":
            pos += 1
        while pos < len(self.buffer) and self.buffer[pos] != " ":
            pos += 1
        self.cursor = min(len(self.buffer), pos)

    def move_start(self) -> None:
        """Move cursor to start of line (Ctrl+I)."""
        self.cursor = 0

    def move_end(self) -> None:
        """Move cursor to end of line (Ctrl+A)."""
        self.cursor = len(self.buffer)

    def clear(self) -> None:
        """Clear buffer and reset cursor."""
        self.buffer = ""
        self.cursor = 0

    def render(self, prompt: str = ">>> ") -> Text:
        """Render prompt with cursor indicator."""
        text = Text()
        text.append(prompt, style=f"bold {Theme.prompt}")
        text.append(self.buffer[: self.cursor])
        if self.cursor < len(self.buffer):
            text.append(self.buffer[self.cursor], style=Theme.cursor)
            text.append(self.buffer[self.cursor + 1 :])
        else:
            text.append(" ", style=Theme.cursor)
        return text
