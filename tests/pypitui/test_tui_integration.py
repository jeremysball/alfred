"""Integration tests for TUI history and keyboard shortcuts.

Tests the integration of HistoryManager and key bindings with AlfredTUI.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from pypitui import Key

if TYPE_CHECKING:
    pass


class TestTUIHistoryIntegration:
    """Test history integration with AlfredTUI."""

    def test_tui_initializes_history_manager(self, tmp_path: Path) -> None:
        """Test that AlfredTUI initializes HistoryManager on startup."""
        from alfred.interfaces.pypitui.history_cache import HistoryManager
        from alfred.interfaces.pypitui.tui import AlfredTUI

        # Mock Alfred
        mock_alfred = MagicMock()
        mock_alfred.config.use_markdown_rendering = True
        mock_alfred.model_name = "test-model"
        mock_alfred.token_tracker.usage.input_tokens = 0
        mock_alfred.token_tracker.usage.output_tokens = 0
        mock_alfred.token_tracker.usage.cache_read_tokens = 0
        mock_alfred.token_tracker.usage.reasoning_tokens = 0
        mock_alfred.token_tracker.context_tokens = 0

        # Mock terminal
        mock_terminal = MagicMock()
        mock_terminal.get_size.return_value = (80, 24)

        # Create history manager with temp directory
        cache_dir = tmp_path / "cache"
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        history_manager = HistoryManager(work_dir, cache_dir)

        with patch("alfred.interfaces.pypitui.tui.TUI") as mock_tui_class:
            mock_tui = MagicMock()
            mock_tui_class.return_value = mock_tui

            tui = AlfredTUI(mock_alfred, terminal=mock_terminal, history_manager=history_manager)

            # History manager should be initialized
            assert hasattr(tui, "_history_manager")
            assert tui._history_manager is not None

    def test_submit_adds_to_history(self, tmp_path: Path) -> None:
        """Test that submitting a message adds it to history."""
        from alfred.interfaces.pypitui.history_cache import HistoryManager
        from alfred.interfaces.pypitui.tui import AlfredTUI

        mock_alfred = MagicMock()
        mock_alfred.config.use_markdown_rendering = True
        mock_alfred.model_name = "test-model"
        mock_alfred.token_tracker.usage.input_tokens = 0
        mock_alfred.token_tracker.usage.output_tokens = 0
        mock_alfred.token_tracker.usage.cache_read_tokens = 0
        mock_alfred.token_tracker.usage.reasoning_tokens = 0
        mock_alfred.token_tracker.context_tokens = 0
        mock_alfred.core.session_manager.has_active_session.return_value = False

        mock_terminal = MagicMock()
        mock_terminal.get_size.return_value = (80, 24)

        # Create history manager with temp directory
        cache_dir = tmp_path / "cache"
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        history_manager = HistoryManager(work_dir, cache_dir)

        with patch("alfred.interfaces.pypitui.tui.TUI") as mock_tui_class:
            mock_tui = MagicMock()
            mock_tui_class.return_value = mock_tui

            tui = AlfredTUI(mock_alfred, terminal=mock_terminal, history_manager=history_manager)

            # Add a message to history
            tui._history_manager.add("test message")

            assert tui._history_manager.size == 1
            assert tui._history_manager._history[0].message == "test message"

    def test_history_cleared_on_new_session(self, tmp_path: Path) -> None:
        """Test that history is cleared when starting a new session."""
        from alfred.interfaces.pypitui.history_cache import HistoryManager
        from alfred.interfaces.pypitui.tui import AlfredTUI

        mock_alfred = MagicMock()
        mock_alfred.config.use_markdown_rendering = True
        mock_alfred.model_name = "test-model"
        mock_alfred.token_tracker.usage.input_tokens = 0
        mock_alfred.token_tracker.usage.output_tokens = 0
        mock_alfred.token_tracker.usage.cache_read_tokens = 0
        mock_alfred.token_tracker.usage.reasoning_tokens = 0
        mock_alfred.token_tracker.context_tokens = 0
        mock_alfred.core.session_manager.has_active_session.return_value = False

        mock_terminal = MagicMock()
        mock_terminal.get_size.return_value = (80, 24)

        # Create history manager with temp directory
        cache_dir = tmp_path / "cache"
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        history_manager = HistoryManager(work_dir, cache_dir)

        with patch("alfred.interfaces.pypitui.tui.TUI") as mock_tui_class:
            mock_tui = MagicMock()
            mock_tui_class.return_value = mock_tui

            tui = AlfredTUI(mock_alfred, terminal=mock_terminal, history_manager=history_manager)

            # Add some history
            tui._history_manager.add("message 1")
            tui._history_manager.add("message 2")
            assert tui._history_manager.size == 2

            # Clear history (simulating /new command)
            tui._history_manager.clear()

            assert tui._history_manager.is_empty


class TestTUIKeyboardShortcuts:
    """Test keyboard shortcuts in TUI."""

    def test_tui_initializes_key_handlers(self, tmp_path: Path) -> None:
        """Test that AlfredTUI initializes key handlers."""
        from alfred.interfaces.pypitui.history_cache import HistoryManager
        from alfred.interfaces.pypitui.tui import AlfredTUI

        mock_alfred = MagicMock()
        mock_alfred.config.use_markdown_rendering = True
        mock_alfred.model_name = "test-model"
        mock_alfred.token_tracker.usage.input_tokens = 0
        mock_alfred.token_tracker.usage.output_tokens = 0
        mock_alfred.token_tracker.usage.cache_read_tokens = 0
        mock_alfred.token_tracker.usage.reasoning_tokens = 0
        mock_alfred.token_tracker.context_tokens = 0

        mock_terminal = MagicMock()
        mock_terminal.get_size.return_value = (80, 24)

        # Create history manager with temp directory
        cache_dir = tmp_path / "cache"
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        history_manager = HistoryManager(work_dir, cache_dir)

        with patch("alfred.interfaces.pypitui.tui.TUI") as mock_tui_class:
            mock_tui = MagicMock()
            mock_tui_class.return_value = mock_tui

            tui = AlfredTUI(mock_alfred, terminal=mock_terminal, history_manager=history_manager)

            # Key handlers should be initialized
            assert hasattr(tui, "_history_handler")
            assert hasattr(tui, "_basic_handler")
            assert tui._history_handler is not None
            assert tui._basic_handler is not None

    def test_input_listener_handles_history_up(self, tmp_path: Path) -> None:
        """Test that input listener handles Up arrow for history."""
        from alfred.interfaces.pypitui.history_cache import HistoryManager
        from alfred.interfaces.pypitui.tui import AlfredTUI

        mock_alfred = MagicMock()
        mock_alfred.config.use_markdown_rendering = True
        mock_alfred.model_name = "test-model"
        mock_alfred.token_tracker.usage.input_tokens = 0
        mock_alfred.token_tracker.usage.output_tokens = 0
        mock_alfred.token_tracker.usage.cache_read_tokens = 0
        mock_alfred.token_tracker.usage.reasoning_tokens = 0
        mock_alfred.token_tracker.context_tokens = 0
        mock_alfred.core.session_manager.has_active_session.return_value = False

        mock_terminal = MagicMock()
        mock_terminal.get_size.return_value = (80, 24)

        # Create history manager with temp directory
        cache_dir = tmp_path / "cache"
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        history_manager = HistoryManager(work_dir, cache_dir)

        with patch("alfred.interfaces.pypitui.tui.TUI") as mock_tui_class:
            mock_tui = MagicMock()
            mock_tui_class.return_value = mock_tui

            tui = AlfredTUI(mock_alfred, terminal=mock_terminal, history_manager=history_manager)

            # Add history entry
            tui._history_manager.add("previous message")

            # Mock input field - need _cursor_pos for _get_input_cursor_line
            tui.input_field.get_value = MagicMock(return_value="")
            tui.input_field.set_value = MagicMock()
            tui.input_field.set_cursor_pos = MagicMock()
            tui.input_field._cursor_pos = 0  # Cursor at position 0 (first line)

            # Simulate Up arrow - should be handled by history
            def mock_matches_key(data, key):
                # Only match UP arrow
                return key == Key.up and data == "\x1b[A"

            with patch("alfred.interfaces.pypitui.tui.matches_key", side_effect=mock_matches_key):
                # Create mock key data
                key_data = "\x1b[A"  # Up arrow escape sequence

                # Call input listener
                result = tui._input_listener(key_data)

                # Should consume the key
                assert result is not None
                assert result.get("consume") is True

    def test_input_listener_ignores_unhandled_keys(self, tmp_path: Path) -> None:
        """Test that input listener ignores unhandled keys."""
        from alfred.interfaces.pypitui.history_cache import HistoryManager
        from alfred.interfaces.pypitui.tui import AlfredTUI

        mock_alfred = MagicMock()
        mock_alfred.config.use_markdown_rendering = True
        mock_alfred.model_name = "test-model"
        mock_alfred.token_tracker.usage.input_tokens = 0
        mock_alfred.token_tracker.usage.output_tokens = 0
        mock_alfred.token_tracker.usage.cache_read_tokens = 0
        mock_alfred.token_tracker.usage.reasoning_tokens = 0
        mock_alfred.token_tracker.context_tokens = 0

        mock_terminal = MagicMock()
        mock_terminal.get_size.return_value = (80, 24)

        # Create history manager with temp directory
        cache_dir = tmp_path / "cache"
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        history_manager = HistoryManager(work_dir, cache_dir)

        with patch("alfred.interfaces.pypitui.tui.TUI") as mock_tui_class:
            mock_tui = MagicMock()
            mock_tui_class.return_value = mock_tui

            tui = AlfredTUI(mock_alfred, terminal=mock_terminal, history_manager=history_manager)

            # Regular character should not be consumed
            with patch("alfred.interfaces.pypitui.tui.matches_key") as mock_matches:
                mock_matches.return_value = False

                result = tui._input_listener("a")

                # Should not consume regular keys
                assert result is None
