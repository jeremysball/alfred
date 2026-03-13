"""Keyboard shortcuts and history navigation for TUI.

Provides:
- History navigation (Up/Down arrows)
- Basic editing shortcuts (Ctrl+A, Ctrl+E, Ctrl+U, Ctrl+L)
- Word navigation (Ctrl+Left/Right arrow)
- Vim-style shortcuts (Ctrl+6/^ for start, Ctrl+4/$ for end)
- Shortcut help display
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.history_cache import HistoryManager


class InputWidget(Protocol):
    """Protocol for input widgets that can work with key bindings."""

    def get_value(self) -> str: ...
    def set_value(self, text: str) -> None: ...
    def set_cursor_pos(self, pos: int) -> None: ...
    @property
    def _cursor_pos(self) -> int: ...


class HistoryKeyHandler:
    """Handles history navigation with Up/Down arrows.

    Integrates HistoryManager with an input widget to provide
    bash-like history recall functionality.
    """

    def __init__(self, history: HistoryManager, input_widget: InputWidget) -> None:
        """Initialize handler.

        Args:
            history: HistoryManager instance
            input_widget: Input widget to manipulate
        """
        self._history = history
        self._input = input_widget

    def on_history_up(self) -> bool:
        """Handle Up arrow - navigate to older history.

        Returns:
            True if handled, False if no history
        """
        current = self._input.get_value()
        new_text = self._history.navigate_up(current)

        if new_text == current and self._history.is_empty:
            return False  # No history

        self._input.set_value(new_text)
        self._input.set_cursor_pos(len(new_text))
        return True

    def on_history_down(self) -> bool:
        """Handle Down arrow - navigate to newer history.

        Returns:
            True if handled, False if not navigating history
        """
        # Only handle if we're currently navigating history (index > 0)
        # or if history is not empty (we might return to saved input)
        if not self._history.is_navigating and self._history.is_empty:
            return False

        new_text = self._history.navigate_down()
        self._input.set_value(new_text)
        self._input.set_cursor_pos(len(new_text))
        return True

    def add_to_history(self, text: str) -> None:
        """Add a message to history.

        Should be called after successful message submission.

        Args:
            text: Message text to add
        """
        self._history.add(text)


class BasicKeyHandler:
    """Handles basic editing shortcuts.

    - Ctrl+U: Clear from cursor to start of line
    - Ctrl+A: Move to start of line
    - Ctrl+E: Move to end of line
    - Ctrl+L: Clear screen (handled at TUI level)
    - Ctrl+Left/Right: Move by word
    - Ctrl+6/^: Move to start of line (vim-style)
    - Ctrl+4/$: Move to end of line (vim-style)
    """

    # Regex for finding word boundaries
    # Matches sequences of alphanumeric chars (words) or non-alphanumeric (non-words)
    WORD_PATTERN = re.compile(r"\w+|\W+")

    def __init__(self, input_widget: InputWidget) -> None:
        """Initialize handler.

        Args:
            input_widget: Input widget to manipulate
        """
        self._input = input_widget

    def on_clear_line(self) -> bool:
        """Handle Ctrl+U - clear from cursor to start.

        Returns:
            True (always handled)
        """
        text = self._input.get_value()
        cursor_pos = self._input._cursor_pos

        # Delete from cursor to start
        new_text = text[cursor_pos:]
        self._input.set_value(new_text)
        self._input.set_cursor_pos(0)
        return True

    def on_start_of_line(self) -> bool:
        """Handle Ctrl+A - move to start of line.

        Returns:
            True (always handled)
        """
        self._input.set_cursor_pos(0)
        return True

    def on_end_of_line(self) -> bool:
        """Handle Ctrl+E - move to end of line.

        Returns:
            True (always handled)
        """
        text = self._input.get_value()
        self._input.set_cursor_pos(len(text))
        return True

    def on_word_left(self) -> bool:
        """Handle Ctrl+Left - move to start of previous word.

        Returns:
            True if moved, False if already at start
        """
        text = self._input.get_value()
        cursor_pos = self._input._cursor_pos

        if cursor_pos <= 0:
            return False

        # Get text before cursor
        before = text[:cursor_pos]

        # Find all word/non-word sequences
        matches = list(self.WORD_PATTERN.finditer(before))

        if not matches:
            self._input.set_cursor_pos(0)
            return True

        # Start from the end and find the previous word
        # Skip any non-word chars at the immediate left of cursor
        for i in range(len(matches) - 1, -1, -1):
            match = matches[i]
            # If this match ends at cursor and is non-word, skip it
            if match.end() == cursor_pos and not match.group().strip():
                continue
            # Move to start of this token
            new_pos = match.start()
            if new_pos < cursor_pos:
                self._input.set_cursor_pos(new_pos)
                return True

        self._input.set_cursor_pos(0)
        return True

    def on_word_right(self) -> bool:
        """Handle Ctrl+Right - move to start of next word.

        Returns:
            True if moved, False if already at end
        """
        text = self._input.get_value()
        cursor_pos = self._input._cursor_pos

        if cursor_pos >= len(text):
            return False

        # Get text after cursor
        after = text[cursor_pos:]

        # Find all word/non-word sequences
        matches = list(self.WORD_PATTERN.finditer(after))

        if not matches:
            self._input.set_cursor_pos(len(text))
            return True

        # Find the next word boundary
        for match in matches:
            # If this match starts at cursor and is non-word, skip it
            if match.start() == 0 and not match.group().strip():
                continue
            # Move past this token
            new_pos = cursor_pos + match.end()
            if new_pos > cursor_pos:
                self._input.set_cursor_pos(min(new_pos, len(text)))
                return True

        self._input.set_cursor_pos(len(text))
        return True

    def on_vim_start_of_line(self) -> bool:
        """Handle Ctrl+6/^ - move to start of line (vim-style).

        Returns:
            True (always handled)
        """
        self._input.set_cursor_pos(0)
        return True

    def on_vim_end_of_line(self) -> bool:
        """Handle Ctrl+4/$ - move to end of line (vim-style).

        Returns:
            True (always handled)
        """
        text = self._input.get_value()
        self._input.set_cursor_pos(len(text))
        return True


class ShortcutHelp:
    """Provides help text for keyboard shortcuts."""

    SHORTCUTS: list[tuple[str, str]] = [
        ("↑/↓", "History navigation"),
        ("Ctrl+C", "Copy / Cancel / Exit"),
        ("Ctrl+L", "Clear screen"),
        ("Ctrl+U", "Clear line"),
        ("Ctrl+A/E", "Start/End of line"),
        ("Ctrl+←/→", "Move by word"),
        ("Ctrl+6/^", "Vim: start of line"),
        ("Ctrl+4/$", "Vim: end of line"),
    ]

    @classmethod
    def get_help_text(cls) -> str:
        """Get formatted help text.

        Returns:
            Multi-line string with aligned shortcuts
        """
        lines = ["Keyboard Shortcuts:", ""]

        # Calculate column width for alignment
        max_key_len = max(len(key) for key, _ in cls.SHORTCUTS)

        for key, description in cls.SHORTCUTS:
            lines.append(f"  {key:<{max_key_len}}  {description}")

        return "\n".join(lines)

    @classmethod
    def get_short_summary(cls) -> str:
        """Get short summary for status line.

        Returns:
            Short string with key shortcuts
        """
        return "Shortcuts: ↑↓ history | Ctrl+L clear | Ctrl+U clear line"
