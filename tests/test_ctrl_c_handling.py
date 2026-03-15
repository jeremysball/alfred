"""Tests for Ctrl+C handling in the TUI."""

from unittest.mock import MagicMock

from alfred.interfaces.pypitui.tui import AlfredTUI


class TestCtrlCHandling:
    """Test the Ctrl+C exit behavior."""

    def test_first_ctrl_c_with_input_clears_and_shows_hint(self):
        """First Ctrl+C with text input should clear input and show toast."""
        # Create mock alfred and dependencies
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

        mock_toast_manager = MagicMock()

        # Create TUI
        tui = AlfredTUI(
            alfred=mock_alfred,
            terminal=mock_terminal,
            toast_manager=mock_toast_manager,
        )

        # Set some input text
        tui.input_field.set_value("some text")
        assert tui.input_field.get_value() == "some text"
        assert not tui._ctrl_c_pending

        # First Ctrl+C should clear input and set pending
        tui._handle_ctrl_c()

        assert tui.input_field.get_value() == ""
        assert tui._ctrl_c_pending
        assert tui.running  # Should NOT exit yet
        mock_toast_manager.add.assert_called_once_with(
            "Press Ctrl-C again to exit",
            level="info",
        )

    def test_second_ctrl_c_after_clear_exits_immediately(self):
        """Second Ctrl+C after input was cleared should exit immediately."""
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

        mock_toast_manager = MagicMock()

        tui = AlfredTUI(
            alfred=mock_alfred,
            terminal=mock_terminal,
            toast_manager=mock_toast_manager,
        )

        # Simulate: type text, first Ctrl+C clears it
        tui.input_field.set_value("some text")
        tui._handle_ctrl_c()  # First Ctrl+C - clears input

        assert tui.input_field.get_value() == ""
        assert tui._ctrl_c_pending
        assert tui.running  # Still running

        # Second Ctrl+C should exit (input is empty)
        tui._handle_ctrl_c()  # Second Ctrl+C - should exit

        assert not tui.running  # Should exit

    def test_ctrl_c_empty_input_exits_immediately(self):
        """Ctrl+C with empty input should exit immediately."""
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

        tui = AlfredTUI(
            alfred=mock_alfred,
            terminal=mock_terminal,
            toast_manager=None,
        )

        # Empty input
        tui.input_field.set_value("")
        assert not tui._ctrl_c_pending

        # Ctrl+C should exit immediately
        tui._handle_ctrl_c()

        assert not tui.running  # Should exit immediately

    def test_other_key_resets_ctrl_c_pending_state(self):
        """Pressing any other key should reset the Ctrl+C pending state."""
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

        tui = AlfredTUI(
            alfred=mock_alfred,
            terminal=mock_terminal,
            toast_manager=None,
        )

        # Simulate: type text, first Ctrl+C clears it and sets pending
        tui.input_field.set_value("some text")
        tui._handle_ctrl_c()

        assert tui._ctrl_c_pending  # Pending state set

        # Now simulate pressing another key (like 'a')
        # This should reset the pending state
        tui._reset_ctrl_c_state()

        assert not tui._ctrl_c_pending  # Should be reset

        # Type something new
        tui.input_field.set_value("new text")

        # Now Ctrl+C should clear input again (not exit)
        tui._handle_ctrl_c()

        assert tui.input_field.get_value() == ""
        assert tui._ctrl_c_pending  # Set again
        assert tui.running  # Should NOT exit
