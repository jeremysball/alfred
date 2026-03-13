"""Tests for keyboard shortcuts and history integration.

All tests use shared fixtures from conftest.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    pass


class TestHistoryIntegration:
    """Test history navigation integrated with input field."""

    def test_history_navigate_up_populates_input(self, tmp_path: Path) -> None:
        """Test that navigate_up populates input field with history."""
        from alfred.interfaces.pypitui.history_cache import HistoryManager
        from alfred.interfaces.pypitui.key_bindings import HistoryKeyHandler

        # Setup
        cache_dir = tmp_path / "cache"
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        history = HistoryManager(work_dir, cache_dir)
        history.add("first message")
        history.add("second message")

        # Mock input field
        mock_input = MagicMock()
        mock_input.get_value.return_value = ""
        mock_input.set_value = MagicMock()
        mock_input.set_cursor_pos = MagicMock()

        handler = HistoryKeyHandler(history, mock_input)

        # Navigate up
        result = handler.on_history_up()

        assert result is True
        mock_input.set_value.assert_called_once_with("second message")
        mock_input.set_cursor_pos.assert_called_once_with(len("second message"))

    def test_history_navigate_down_returns_to_input(self, tmp_path: Path) -> None:
        """Test that navigate_down returns to saved input."""
        from alfred.interfaces.pypitui.history_cache import HistoryManager
        from alfred.interfaces.pypitui.key_bindings import HistoryKeyHandler

        # Setup
        cache_dir = tmp_path / "cache"
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        history = HistoryManager(work_dir, cache_dir)
        history.add("message")

        # Mock input field
        mock_input = MagicMock()
        mock_input.get_value.return_value = "typed input"
        mock_input.set_value = MagicMock()
        mock_input.set_cursor_pos = MagicMock()

        handler = HistoryKeyHandler(history, mock_input)

        # Go up then down
        handler.on_history_up()
        mock_input.reset_mock()

        result = handler.on_history_down()

        assert result is True
        mock_input.set_value.assert_called_once_with("typed input")
        mock_input.set_cursor_pos.assert_called_once_with(len("typed input"))

    def test_history_empty_does_nothing(self, tmp_path: Path) -> None:
        """Test that empty history doesn't change input."""
        from alfred.interfaces.pypitui.history_cache import HistoryManager
        from alfred.interfaces.pypitui.key_bindings import HistoryKeyHandler

        cache_dir = tmp_path / "cache"
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        history = HistoryManager(work_dir, cache_dir)

        mock_input = MagicMock()
        mock_input.get_value.return_value = "current"
        mock_input.set_value = MagicMock()

        handler = HistoryKeyHandler(history, mock_input)

        result = handler.on_history_up()

        assert result is False
        mock_input.set_value.assert_not_called()


class TestBasicShortcuts:
    """Test basic keyboard shortcuts."""

    def test_clear_line(self) -> None:
        """Test Ctrl+U clears the current line."""
        from alfred.interfaces.pypitui.key_bindings import BasicKeyHandler

        mock_input = MagicMock()
        mock_input.get_value.return_value = "some text here"
        mock_input._cursor_pos = 5  # Cursor in middle
        mock_input.set_value = MagicMock()
        mock_input.set_cursor_pos = MagicMock()

        handler = BasicKeyHandler(mock_input)
        result = handler.on_clear_line()

        assert result is True
        # Should clear from cursor to start (clears "some ")
        mock_input.set_value.assert_called_once_with("text here")
        mock_input.set_cursor_pos.assert_called_once_with(0)

    def test_start_of_line(self) -> None:
        """Test Ctrl+A moves cursor to start."""
        from alfred.interfaces.pypitui.key_bindings import BasicKeyHandler

        mock_input = MagicMock()
        mock_input._cursor_pos = 10
        mock_input.set_cursor_pos = MagicMock()

        handler = BasicKeyHandler(mock_input)
        result = handler.on_start_of_line()

        assert result is True
        mock_input.set_cursor_pos.assert_called_once_with(0)

    def test_end_of_line(self) -> None:
        """Test Ctrl+E moves cursor to end."""
        from alfred.interfaces.pypitui.key_bindings import BasicKeyHandler

        mock_input = MagicMock()
        mock_input.get_value.return_value = "test text"
        mock_input._cursor_pos = 2
        mock_input.set_cursor_pos = MagicMock()

        handler = BasicKeyHandler(mock_input)
        result = handler.on_end_of_line()

        assert result is True
        mock_input.set_cursor_pos.assert_called_once_with(9)


class TestShortcutHelp:
    """Test shortcut help display."""

    def test_help_text_contains_shortcuts(self) -> None:
        """Test that help text lists all shortcuts."""
        from alfred.interfaces.pypitui.key_bindings import ShortcutHelp

        help_text = ShortcutHelp.get_help_text()

        assert "Up/Down" in help_text or "↑/↓" in help_text
        assert "Ctrl+C" in help_text
        assert "Ctrl+L" in help_text
        assert "Ctrl+U" in help_text
        assert "Ctrl+A" in help_text or "Ctrl+A/E" in help_text
