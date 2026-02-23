"""Rich Live display with custom prompt input.

This module provides a flicker-free streaming display using Rich Live,
with a custom prompt that supports editing, history, and tab completion.
"""

from enum import Enum, auto

from readchar import readkey
from rich.console import Console
from rich.live import Live
from rich.text import Text

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


class KeyAction(Enum):
    """Actions triggered by keypresses."""

    INSERT = auto()
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
    ENTER = auto()
    ESC = auto()
    SUBMIT = auto()


class InputReader:
    """Read keyboard input and translate to actions."""

    def read(self) -> tuple[KeyAction, str]:
        """Read a keypress and return (action, char).

        char is populated for INSERT action, empty string otherwise.
        """
        key = readkey()

        # Arrow and special keys
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
        elif key == ESC:
            return (KeyAction.ESC, "")
        elif key == TAB:
            return (KeyAction.TAB, "")
        elif key == SHIFT_TAB:
            return (KeyAction.SHIFT_TAB, "")

        # Ctrl keys
        elif key == "\x01":  # Ctrl+A (end of line per user preference)
            return (KeyAction.END, "")
        elif key == "\x09":  # Ctrl+I (same code as Tab)
            # readchar returns TAB constant, not this, so this is for safety
            return (KeyAction.TAB, "")
        elif key == "\x0b":  # Ctrl+K
            return (KeyAction.DELETE_TO_END, "")
        elif key == "\x15":  # Ctrl+U
            return (KeyAction.DELETE_TO_START, "")
        elif key == "\x17":  # Ctrl+W
            return (KeyAction.DELETE_WORD, "")

        # Alt sequences (ESC + char)
        elif key.startswith("\x1b") and len(key) > 1:
            rest = key[1:]
            if rest == "b":  # Alt+B - back word
                return (KeyAction.WORD_LEFT, "")
            elif rest == "f":  # Alt+F - forward word
                return (KeyAction.WORD_RIGHT, "")
            elif rest in ("[1;3D", "[1;5D"):  # Various Alt+Left encodings
                return (KeyAction.WORD_LEFT, "")
            elif rest in ("[1;3C", "[1;5C"):  # Various Alt+Right encodings
                return (KeyAction.WORD_RIGHT, "")
            return (KeyAction.ESC, "")

        # Printable characters
        if key.isprintable():
            return (KeyAction.INSERT, key)

        # Unknown key
        return (KeyAction.ESC, "")


class PromptInput:
    """Custom input buffer with cursor tracking."""

    def __init__(self) -> None:
        self.buffer: str = ""
        self.cursor: int = 0  # Position in buffer

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
        # Find start of word
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
        """Render prompt with cursor indicator.

        Returns Rich Text with cursor shown as reversed character or space.
        """
        text = Text()
        text.append(prompt, style="bold green")

        # Pre-cursor
        text.append(self.buffer[: self.cursor])
        # Cursor position
        if self.cursor < len(self.buffer):
            # Reverse the character at cursor
            text.append(self.buffer[self.cursor], style="reverse")
            # Post-cursor
            text.append(self.buffer[self.cursor + 1 :])
        else:
            # Cursor at end, show reversed space
            text.append(" ", style="reverse")

        return text


class History:
    """Command history with file persistence.

    History is stored in session meta files, not a global file.
    The session code passes the appropriate path when creating LiveDisplay.
    """

    def __init__(self, filepath: str | None = None) -> None:
        from pathlib import Path

        self.filepath: Path | None = Path(filepath).expanduser() if filepath else None
        self.entries: list[str] = []
        self.index: int = -1  # -1 means not navigating
        self._load()

    def _load(self) -> None:
        """Load history from file."""
        if self.filepath and self.filepath.exists():
            self.entries = self.filepath.read_text().splitlines()

    def _save(self) -> None:
        """Save history to file."""
        if self.filepath:
            self.filepath.write_text("\n".join(self.entries[-1000:]))  # Keep last 1000

    def add(self, command: str) -> None:
        """Add command to history."""
        if command.strip():  # Don't add empty commands
            self.entries.append(command)
            self._save()
        self.index = -1

    def up(self, current: str) -> str:
        """Go up in history, return that entry."""
        if not self.entries:
            return current
        if self.index == -1:
            # Start navigating from end
            self.index = len(self.entries) - 1
        elif self.index > 0:
            self.index -= 1
        return self.entries[self.index]

    def down(self, current: str) -> str:
        """Go down in history, return that entry or original."""
        if self.index == -1:
            return current
        if self.index < len(self.entries) - 1:
            self.index += 1
            return self.entries[self.index]
        else:
            # Back to original
            self.index = -1
            return current


class LiveDisplay:
    """Rich Live display with streaming content and custom prompt."""

    def __init__(
        self,
        console: Console | None = None,
        status_text: str = "Ready",
        history_path: str | None = None,
    ) -> None:
        self.console = console or Console()
        self.status_text = status_text
        self.content: str = ""  # Accumulated markdown content
        self.prompt = PromptInput()
        self.history = History(history_path)
        self.reader = InputReader()
        self._live: Live | None = None

    def set_status(self, text: str) -> None:
        """Update status line text."""
        self.status_text = text
        self._refresh()

    def add_content(self, text: str) -> None:
        """Add text to content buffer (for streaming)."""
        self.content += text
        self._refresh()

    def clear_content(self) -> None:
        """Clear content buffer (new message)."""
        self.content = ""
        self._refresh()

    def _render(self) -> Text:
        """Render full display: content + prompt + status."""
        text = Text()

        # Content section
        if self.content:
            text.append(self.content)
            if not self.content.endswith("\n"):
                text.append("\n")

        # Prompt section
        text.append(self.prompt.render())
        text.append("\n")

        # Status line
        text.append(self.status_text, style="dim")

        return text

    def _refresh(self) -> None:
        """Refresh Live display if active."""
        if self._live is not None:
            self._live.update(self._render())

    def start(self) -> None:
        """Start Live display."""
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=20,  # 50ms throttle
        )
        self._live.start()

    def stop(self) -> None:
        """Stop Live display."""
        if self._live is not None:
            self._live.stop()
            self._live = None

    def __enter__(self) -> "LiveDisplay":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()

    def read_line(self) -> str:
        """Read a line of input with editing support.

        Returns the submitted string.
        """
        self.prompt.clear()

        while True:
            action, char = self.reader.read()

            if action == KeyAction.INSERT:
                self.prompt.insert(char)
            elif action == KeyAction.BACKSPACE:
                self.prompt.delete_left()
            elif action == KeyAction.DELETE:
                self.prompt.delete_right()
            elif action == KeyAction.DELETE_TO_END:
                self.prompt.delete_to_end()
            elif action == KeyAction.DELETE_TO_START:
                self.prompt.delete_to_start()
            elif action == KeyAction.DELETE_WORD:
                self.prompt.delete_word()
            elif action == KeyAction.LEFT:
                self.prompt.move_left()
            elif action == KeyAction.RIGHT:
                self.prompt.move_right()
            elif action == KeyAction.WORD_LEFT:
                self.prompt.move_word_left()
            elif action == KeyAction.WORD_RIGHT:
                self.prompt.move_word_right()
            elif action == KeyAction.START:
                self.prompt.move_start()
            elif action == KeyAction.END:
                self.prompt.move_end()
            elif action == KeyAction.UP:
                # History up
                new_val = self.history.up(self.prompt.buffer)
                self.prompt.buffer = new_val
                self.prompt.cursor = len(new_val)
            elif action == KeyAction.DOWN:
                # History down
                new_val = self.history.down(self.prompt.buffer)
                self.prompt.buffer = new_val
                self.prompt.cursor = len(new_val)
            elif action == KeyAction.ENTER:
                # Submit
                result = self.prompt.buffer
                self.history.add(result)
                self.prompt.clear()
                return result
            elif action == KeyAction.TAB:
                # TODO: Tab completion
                pass
            elif action == KeyAction.SHIFT_TAB:
                # TODO: Reverse tab completion
                pass
            elif action == KeyAction.ESC:
                # TODO: Handle ESC (dismiss dropdown, etc.)
                pass

            self._refresh()
