"""Rich Live display with custom prompt input.

This module provides a flicker-free streaming display using Rich Live,
with a custom prompt that supports editing, history, and tab completion.
"""

import asyncio
import sys
import termios
import select
import time
from collections.abc import Callable
from enum import Enum, auto
from typing import Any

from readchar import readkey
from rich.console import Console, Group, RenderableType
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
        elif key == "\x1b[13;2u" or key == "\x1b[13;2~":  # Shift+Enter (kitty and other protocols)
            return (KeyAction.SHIFT_ENTER, "")
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
            elif rest == "[1;3D":  # Alt+Left
                return (KeyAction.WORD_LEFT, "")
            elif rest == "[1;3C":  # Alt+Right
                return (KeyAction.WORD_RIGHT, "")
            elif rest == "[1;5D":  # Ctrl+Left
                return (KeyAction.WORD_LEFT, "")
            elif rest == "[1;5C":  # Ctrl+Right
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
        self._original_input: str = ""  # Store original input when navigating
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
        self._original_input = ""  # Clear original input

    def up(self, current: str) -> str:
        """Go up in history, return that entry."""
        if not self.entries:
            return current
        if self.index == -1:
            # Start navigating from end - save original input
            self._original_input = current
            self.index = len(self.entries) - 1
        elif self.index > 0:
            self.index -= 1
        return self.entries[self.index]

    def down(self, current: str) -> str:
        """Go down in history, return that entry or clear if at end."""
        if self.index == -1:
            return current
        if self.index < len(self.entries) - 1:
            self.index += 1
            return self.entries[self.index]
        else:
            # Back to original input, then clear on next down
            self.index = -1
            result = self._original_input
            self._original_input = ""  # Clear for next navigation
            return result


class Completer:
    """Tab completion with fuzzy matching for commands, tools, and file paths."""

    # Slash commands (static)
    STATIC_COMMANDS = [
        "/help",
        "/session",
        "/sessions",
        "/new",
        "/model",
        "/clear",
        "/exit",
        "/quit",
    ]

    # Tool names (lowercase for matching)
    TOOLS = [
        "remember",
        "forget",
        "search",
        "bash",
        "read",
        "write",
        "edit",
        "schedule",
        "approve",
        "reject",
        "list",
    ]

    def __init__(
        self,
        max_visible: int = 5,
        get_session_ids: Callable[[], list[str]] | None = None,
    ) -> None:
        """Initialize completer.

        Args:
            max_visible: Maximum number of items to show in dropdown.
            get_session_ids: Callback to fetch session IDs for /resume completion.
        """
        self.max_visible = max_visible
        self.get_session_ids = get_session_ids
        self.matches: list[str] = []
        self.selected_index: int = 0
        self._visible: bool = False

    def _fuzzy_match(self, query: str, candidate: str) -> bool:
        """Check if query fuzzy-matches candidate.

        'hp' matches 'help' because h, then p appears after h.
        """
        query = query.lower()
        candidate = candidate.lower()

        q_idx = 0
        for char in candidate:
            if q_idx < len(query) and char == query[q_idx]:
                q_idx += 1
        return q_idx == len(query)

    def _score_match(self, query: str, candidate: str) -> int:
        """Score how good the match is (higher = better)."""
        query = query.lower()
        candidate = candidate.lower()

        # Exact match is best
        if candidate == query:
            return 100

        # Prefix match is good
        if candidate.startswith(query):
            return 80

        # Fuzzy match - score based on how early chars appear
        score = 50
        q_idx = 0
        for i, char in enumerate(candidate):
            if q_idx < len(query) and char == query[q_idx]:
                # Earlier matches score higher
                score += max(0, 10 - i)
                q_idx += 1

        return score

    def get_completions(self, text: str) -> list[str]:
        """Get completion candidates for text.

        Returns list of matches sorted by score (best first).
        """
        if not text:
            return []

        # Detect what we're completing
        if text.startswith("/"):
            # Handle /resume <id> - complete session IDs
            if text.startswith("/resume ") and self.get_session_ids:
                session_id_part = text[8:]  # Text after "/resume "
                candidates = [f"/resume {sid}" for sid in self.get_session_ids()]
                query = text
            else:
                # Command completion
                candidates = self.STATIC_COMMANDS
                query = text
        elif " " not in text:
            # Tool name completion (single word)
            candidates = self.TOOLS
            query = text
        else:
            # File path completion - get last word
            last_word = text.split()[-1]
            if "/" in last_word or last_word.startswith("~"):
                candidates = self._get_file_completions(last_word)
                query = last_word
            else:
                candidates = self.TOOLS
                query = last_word

        # Fuzzy match and score
        scored = []
        for candidate in candidates:
            if self._fuzzy_match(query, candidate):
                score = self._score_match(query, candidate)
                scored.append((score, candidate))

        # Sort by score descending, then alphabetically
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [c for _, c in scored]

    def _get_file_completions(self, partial: str) -> list[str]:
        """Get file path completions."""
        from pathlib import Path

        try:
            # Expand ~ and get directory
            expanded = Path(partial).expanduser()

            if partial.endswith("/"):
                dir_path = expanded
                prefix = ""
            else:
                dir_path = expanded.parent
                prefix = expanded.name

            if not dir_path.exists():
                return []

            # List directory contents
            results = []
            for item in dir_path.iterdir():
                name = item.name
                if name.startswith("."):
                    continue  # Skip hidden files
                if item.is_dir():
                    name += "/"
                results.append(str(dir_path / name))

            # Filter by prefix if any
            if prefix:
                results = [r for r in results if Path(r).name.startswith(prefix)]

            return sorted(results)
        except (OSError, PermissionError):
            return []

    def start(self, text: str) -> bool:
        """Start completion mode. Returns True if matches found."""
        self.matches = self.get_completions(text)
        if self.matches:
            self.selected_index = 0
            self._visible = True
            return True
        return False

    def next(self) -> None:
        """Move to next match."""
        if self.matches:
            self.selected_index = (self.selected_index + 1) % len(self.matches)

    def prev(self) -> None:
        """Move to previous match."""
        if self.matches:
            self.selected_index = (self.selected_index - 1) % len(self.matches)

    def get_selected(self) -> str | None:
        """Get currently selected completion."""
        if self.matches and 0 <= self.selected_index < len(self.matches):
            return self.matches[self.selected_index]
        return None

    def hide(self) -> None:
        """Hide dropdown."""
        self._visible = False
        self.matches = []
        self.selected_index = 0

    @property
    def visible(self) -> bool:
        """Check if dropdown is visible."""
        return self._visible and len(self.matches) > 0

    def render_dropdown(self) -> Text:
        """Render the dropdown as Rich Text."""
        if not self.visible:
            return Text()

        text = Text()

        # Show up to max_visible items, with scroll indicator if more
        start = 0
        if len(self.matches) > self.max_visible:
            # Center selected item in visible window
            start = max(0, self.selected_index - self.max_visible // 2)
            start = min(start, len(self.matches) - self.max_visible)

        visible_matches = self.matches[start : start + self.max_visible]

        for i, match in enumerate(visible_matches):
            actual_index = start + i
            is_selected = actual_index == self.selected_index

            # Truncate long paths
            display = match
            if len(display) > 60:
                display = "..." + display[-57:]

            if is_selected:
                text.append(f"  {display}\n", style="reverse")
            else:
                text.append(f"  {display}\n", style="dim")

        if len(self.matches) > self.max_visible:
            remaining = len(self.matches) - start - self.max_visible
            text.append(f"  └─ {remaining} more\n", style="dim")

        return text


class LiveDisplay:
    """Rich Live display with streaming content and custom prompt.

    Layout (top to bottom):
        - Content area (markdown, tool panels)
        - Dropdown (when tab completion active)
        - Prompt line (>>> with cursor)
        - Status line (model, tokens, context - tmux-style at bottom)
    """

    def __init__(
        self,
        console: Console | None = None,
        history_path: str | None = None,
        get_session_ids: Callable[[], list[str]] | None = None,
    ) -> None:
        """Initialize LiveDisplay.

        Args:
            console: Rich Console instance.
            history_path: Path to history file (session-based).
            get_session_ids: Callback to fetch session IDs for /resume completion.
        """
        self.console = console or Console()
        self.prompt = PromptInput()
        self.history = History(history_path)
        self.reader = InputReader()
        self.completer = Completer(get_session_ids=get_session_ids)
        self._live: Live | None = None

        # Content: list of Rich renderables (panels, markdown, etc.)
        self._content: list[RenderableType] = []

        # Status line: Rich renderable (Text, Columns, etc.)
        self._status: RenderableType = Text("Ready", style="dim")

        # Prompt visibility (hide during streaming)
        self._show_prompt: bool = True

    def _drain_stdin(self) -> None:
        """Drain any buffered stdin input to prevent stale keypresses.
        
        This is critical after streaming ends - any keys pressed during
        streaming (like spamming Enter) must be discarded before we start
        reading input again.
        """
        if not sys.stdin.isatty():
            return
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            # Set to non-canonical, non-blocking with immediate timeout
            new_settings = termios.tcgetattr(fd)
            new_settings[3] = new_settings[3] & ~termios.ICANON & ~termios.ECHO
            new_settings[6][termios.VMIN] = 0
            new_settings[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, new_settings)
            
            # Aggressively drain all pending input
            drained = 0
            while True:
                ready, _, _ = select.select([sys.stdin], [], [], 0)
                if not ready:
                    break
                try:
                    char = sys.stdin.read(1)
                    if not char:
                        break
                    drained += 1
                except (IOError, OSError):
                    break
            
            if drained > 0:
                # Small delay to catch any stragglers, then drain again
                time.sleep(0.01)
                while select.select([sys.stdin], [], [], 0)[0]:
                    try:
                        if not sys.stdin.read(1):
                            break
                        drained += 1
                    except (IOError, OSError):
                        break
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, old_settings)

    def disable_echo(self) -> None:
        """Disable terminal echo - prevents keystrokes from appearing during streaming."""
        if not sys.stdin.isatty():
            return
        
        fd = sys.stdin.fileno()
        # Get current settings and store them
        self._original_tty_settings = termios.tcgetattr(fd)
        new_settings = termios.tcgetattr(fd)
        # Disable ECHO
        new_settings[3] = new_settings[3] & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, new_settings)

    def enable_echo(self) -> None:
        """Re-enable terminal echo after streaming."""
        if not sys.stdin.isatty() or not hasattr(self, '_original_tty_settings'):
            return
        
        fd = sys.stdin.fileno()
        termios.tcsetattr(fd, termios.TCSANOW, self._original_tty_settings)

    def set_content(self, renderables: list[RenderableType]) -> None:
        """Set content area to list of renderables (e.g., ConversationBuffer.render())."""
        self._content = renderables
        self._refresh()

    def add_content(self, renderable: RenderableType) -> None:
        """Add a renderable to content area."""
        self._content.append(renderable)
        self._refresh()

    def clear_content(self) -> None:
        """Clear content area (new message)."""
        self._content = []
        self._refresh()

    def set_status(self, status: RenderableType) -> None:
        """Update status line (tmux-style at bottom).

        Args:
            status: Any Rich renderable (Text, Columns, Panel, etc.)
        """
        self._status = status
        self._refresh()

    def set_prompt_visible(self, visible: bool) -> None:
        """Show or hide the prompt line.

        Hide during streaming to prevent UI corruption from buffered input.

        Args:
            visible: True to show prompt, False to hide.
        """
        self._show_prompt = visible
        self._refresh()

    def _render(self) -> RenderableType:
        """Render full display: content + dropdown + prompt + status."""
        parts: list[RenderableType] = []

        # Content section (panels, markdown, etc.)
        if self._content:
            parts.extend(self._content)

        # Dropdown overlay (above prompt)
        if self.completer.visible:
            parts.append(self.completer.render_dropdown())

        # Prompt section (only when visible)
        if self._show_prompt:
            parts.append(self.prompt.render())

        # Status line at bottom (tmux-style)
        parts.append(self._status)

        return Group(*parts)

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

    def update(self) -> None:
        """Force refresh of Live display (call after external content changes)."""
        self._refresh()

    def __enter__(self) -> "LiveDisplay":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()

    def read_line(self) -> str:
        """Read a line of input with editing support (synchronous).

        Returns the submitted string.
        """
        # Drain any buffered input from previous streaming
        self._drain_stdin()
        
        self.prompt.clear()
        self._show_prompt = True
        self._refresh()  # Show empty prompt initially

        while True:
            action, char = self.reader.read()
            if self._handle_action(action, char):
                result = self.prompt.buffer
                self.history.add(result)
                self.completer.hide()
                self.prompt.clear()
                self._refresh()  # Clear the prompt visually before returning
                return result

    async def read_line_async(self) -> str:
        """Read a line of input with editing support (async).

        Wraps synchronous read_line() in executor to avoid blocking event loop.

        Returns the submitted string.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.read_line)

    def _handle_action(self, action: KeyAction, char: str) -> bool:
        """Handle a key action. Returns True if input should be submitted."""
        # If dropdown is visible, arrow keys navigate it
        if self.completer.visible:
            if action == KeyAction.TAB:
                self.completer.next()
                self._refresh()
                return False
            elif action == KeyAction.SHIFT_TAB:
                self.completer.prev()
                self._refresh()
                return False
            elif action == KeyAction.UP:
                self.completer.prev()
                self._refresh()
                return False
            elif action == KeyAction.DOWN:
                self.completer.next()
                self._refresh()
                return False
            elif action == KeyAction.ENTER:
                # Accept selected completion
                selected = self.completer.get_selected()
                if selected:
                    self._apply_completion(selected)
                    self.completer.hide()
                self._refresh()
                return False
            elif action == KeyAction.ESC:
                self.completer.hide()
                self._refresh()
                return False

        # Normal input handling
        if action == KeyAction.INSERT:
            self.prompt.insert(char)
            self.completer.hide()
        elif action == KeyAction.SHIFT_ENTER:
            # Insert newline for multi-line input
            self.prompt.insert("\n")
            self.completer.hide()
        elif action == KeyAction.BACKSPACE:
            self.prompt.delete_left()
            self.completer.hide()
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
            new_val = self.history.up(self.prompt.buffer)
            self.prompt.buffer = new_val
            self.prompt.cursor = len(new_val)
        elif action == KeyAction.DOWN:
            new_val = self.history.down(self.prompt.buffer)
            self.prompt.buffer = new_val
            self.prompt.cursor = len(new_val)
        elif action == KeyAction.ENTER:
            # Submit
            return True
        elif action == KeyAction.TAB:
            self.completer.start(self.prompt.buffer)
        elif action == KeyAction.SHIFT_TAB:
            pass  # No action when dropdown hidden
        elif action == KeyAction.ESC:
            pass  # No action when dropdown hidden

        self._refresh()
        return False

    def _apply_completion(self, completion: str) -> None:
        """Apply a completion to the current buffer."""
        text = self.prompt.buffer

        # For commands (including /resume <id>), replace entire buffer
        if completion.startswith("/"):
            self.prompt.buffer = completion + " "
            self.prompt.cursor = len(self.prompt.buffer)
            return

        # For file paths, replace last word
        if "/" in completion:
            words = text.split()
            if words:
                self.prompt.buffer = " ".join(words[:-1]) + " " + completion + " "
                if len(words) == 1:
                    self.prompt.buffer = completion + " "
                self.prompt.cursor = len(self.prompt.buffer)
            else:
                self.prompt.buffer = completion + " "
                self.prompt.cursor = len(self.prompt.buffer)
            return

        # For tool names, replace last word
        words = text.split()
        if words:
            self.prompt.buffer = " ".join(words[:-1]) + " " + completion + " "
            if len(words) == 1:
                self.prompt.buffer = completion + " "
            self.prompt.cursor = len(self.prompt.buffer)
        else:
            self.prompt.buffer = completion + " "
            self.prompt.cursor = len(self.prompt.buffer)
