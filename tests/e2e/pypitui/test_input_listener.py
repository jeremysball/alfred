"""Tests for AlfredTUI input listener refactoring."""

from unittest.mock import MagicMock


class TestInputListenerControlKeys:
    """Tests for control key handling in _input_listener."""

    def test_ctrl_u_clears_line(self, mock_alfred, mock_terminal):
        """Ctrl+U should clear from cursor to start of line."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._basic_handler = MagicMock()
        tui._basic_handler.on_clear_line.return_value = True

        result = tui._handle_control_keys("\x15")  # Ctrl+U

        assert result == {"consume": True}
        tui._basic_handler.on_clear_line.assert_called_once()

    def test_ctrl_u_not_consumed_when_handler_fails(self, mock_alfred, mock_terminal):
        """Ctrl+U should not be consumed if handler returns False."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._basic_handler = MagicMock()
        tui._basic_handler.on_clear_line.return_value = False

        result = tui._handle_control_keys("\x15")  # Ctrl+U

        assert result is None

    def test_ctrl_a_moves_to_start(self, mock_alfred, mock_terminal):
        """Ctrl+A should move cursor to start of line."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._basic_handler = MagicMock()
        tui._basic_handler.on_start_of_line.return_value = True

        result = tui._handle_control_keys("\x01")  # Ctrl+A

        assert result == {"consume": True}
        tui._basic_handler.on_start_of_line.assert_called_once()

    def test_ctrl_e_moves_to_end(self, mock_alfred, mock_terminal):
        """Ctrl+E should move cursor to end of line."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._basic_handler = MagicMock()
        tui._basic_handler.on_end_of_line.return_value = True

        result = tui._handle_control_keys("\x05")  # Ctrl+E

        assert result == {"consume": True}
        tui._basic_handler.on_end_of_line.assert_called_once()

    def test_ctrl_l_clears_screen(self, mock_alfred, mock_terminal):
        """Ctrl+L should clear screen and be consumed."""
        from unittest.mock import patch

        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        with patch.object(mock_terminal, 'write') as mock_write:
            result = tui._handle_control_keys("\x0c")  # Ctrl+L

            assert result == {"consume": True}
            mock_write.assert_called_once_with("\x1b[2J\x1b[H")

    def test_ctrl_vim_start_of_line(self, mock_alfred, mock_terminal):
        """Ctrl+6/^ should trigger vim-style start of line."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._basic_handler = MagicMock()
        tui._basic_handler.on_vim_start_of_line.return_value = True

        result = tui._handle_control_keys("\x1e")  # Ctrl+6/^)

        assert result == {"consume": True}
        tui._basic_handler.on_vim_start_of_line.assert_called_once()

    def test_ctrl_vim_end_of_line(self, mock_alfred, mock_terminal):
        """Ctrl+4/$ should trigger vim-style end of line."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._basic_handler = MagicMock()
        tui._basic_handler.on_vim_end_of_line.return_value = True

        result = tui._handle_control_keys("\x1c")  # Ctrl+4/$

        assert result == {"consume": True}
        tui._basic_handler.on_vim_end_of_line.assert_called_once()

    def test_ctrl_left_moves_word_left(self, mock_alfred, mock_terminal):
        """Ctrl+Left should move to previous word."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._basic_handler = MagicMock()
        tui._basic_handler.on_word_left.return_value = True

        result = tui._handle_control_keys("\x1b[1;5D")  # Ctrl+Left

        assert result == {"consume": True}
        tui._basic_handler.on_word_left.assert_called_once()

    def test_ctrl_right_moves_word_right(self, mock_alfred, mock_terminal):
        """Ctrl+Right should move to next word."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._basic_handler = MagicMock()
        tui._basic_handler.on_word_right.return_value = True

        result = tui._handle_control_keys("\x1b[1;5C")  # Ctrl+Right

        assert result == {"consume": True}
        tui._basic_handler.on_word_right.assert_called_once()

    def test_unknown_control_key_returns_none(self, mock_alfred, mock_terminal):
        """Unknown control keys should return None."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        result = tui._handle_control_keys("\x02")  # Ctrl+B (not handled)

        assert result is None


class TestInputListenerEscapeKey:
    """Tests for escape key handling."""

    def test_escape_clears_queue_when_not_empty(self, mock_alfred, mock_terminal):
        """Escape should clear queue and reset state when queue has items."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._message_queue = ["message1", "message2"]
        tui._queue_nav_index = 1
        tui._queue_draft = "draft text"
        tui.input_field.set_value("current text")

        # Mock _update_status to avoid side effects
        tui._update_status = MagicMock()

        # Use the actual escape key through _input_listener

        result = tui._handle_escape_key()

        assert result == {"consume": True}
        assert len(tui._message_queue) == 0
        assert tui._queue_nav_index == -1
        assert tui._queue_draft == ""
        assert tui.input_field.get_value() == ""

    def test_escape_not_consumed_when_queue_empty(self, mock_alfred, mock_terminal):
        """Escape should not be consumed when queue is empty."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._message_queue = []

        result = tui._handle_escape_key()

        assert result is None


class TestInputListenerNavigationKeys:
    """Tests for UP/DOWN arrow navigation."""

    def test_up_arrow_navigates_queue_from_bottom(self, mock_alfred, mock_terminal):
        """UP arrow should enter queue navigation from bottom when on first line."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._message_queue = ["first", "second", "third"]
        tui._queue_nav_index = -1
        tui._queue_draft = ""
        tui.input_field.set_value("current draft")

        result = tui._handle_up_navigation(cursor_line=0)

        assert result == {"consume": True}
        assert tui._queue_nav_index == 2  # Last index
        assert tui._queue_draft == "current draft"
        assert tui.input_field.get_value() == "third"

    def test_up_arrow_navigates_up_in_queue(self, mock_alfred, mock_terminal):
        """UP arrow should navigate up in queue when already in queue nav."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._message_queue = ["first", "second", "third"]
        tui._queue_nav_index = 2
        tui._queue_draft = "draft"
        tui.input_field.set_value("third")

        result = tui._handle_up_navigation(cursor_line=0)

        assert result == {"consume": True}
        assert tui._queue_nav_index == 1
        assert tui.input_field.get_value() == "second"

    def test_up_arrow_at_top_of_queue_consumed(self, mock_alfred, mock_terminal):
        """UP arrow at top of queue should be consumed but not change value."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._message_queue = ["first", "second"]
        tui._queue_nav_index = 0  # At top
        tui.input_field.set_value("first")

        result = tui._handle_up_navigation(cursor_line=0)

        assert result == {"consume": True}
        assert tui._queue_nav_index == 0
        assert tui.input_field.get_value() == "first"

    def test_up_arrow_falls_back_to_history_when_queue_empty(self, mock_alfred, mock_terminal):
        """UP arrow should use history when queue is empty and on first line."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._message_queue = []
        tui._history_handler = MagicMock()
        tui._history_handler.on_history_up.return_value = True

        result = tui._handle_up_navigation(cursor_line=0)

        assert result == {"consume": True}
        tui._history_handler.on_history_up.assert_called_once()

    def test_up_arrow_not_consumed_when_not_on_first_line(self, mock_alfred, mock_terminal):
        """UP arrow should not be consumed when cursor not on first line."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        result = tui._handle_up_navigation(cursor_line=1)

        assert result is None

    def test_down_arrow_navigates_down_in_queue(self, mock_alfred, mock_terminal):
        """DOWN arrow should navigate down in queue."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._message_queue = ["first", "second", "third"]
        tui._queue_nav_index = 0
        tui._queue_draft = "draft"
        tui.input_field.set_value("first")

        result = tui._handle_down_navigation()

        assert result == {"consume": True}
        assert tui._queue_nav_index == 1
        assert tui.input_field.get_value() == "second"

    def test_down_arrow_exits_queue_at_bottom(self, mock_alfred, mock_terminal):
        """DOWN arrow at bottom of queue should exit queue nav and restore draft."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._message_queue = ["first", "second"]
        tui._queue_nav_index = 1  # At bottom
        tui._queue_draft = "original draft"
        tui.input_field.set_value("second")

        result = tui._handle_down_navigation()

        assert result == {"consume": True}
        assert tui._queue_nav_index == -1
        assert tui.input_field.get_value() == "original draft"

    def test_down_arrow_falls_back_to_history_when_not_in_queue(self, mock_alfred, mock_terminal):
        """DOWN arrow should use history when not in queue navigation."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._queue_nav_index = -1  # Not in queue nav
        tui._history_handler = MagicMock()
        tui._history_handler.on_history_down.return_value = True

        result = tui._handle_down_navigation()

        assert result == {"consume": True}
        tui._history_handler.on_history_down.assert_called_once()

    def test_down_arrow_not_consumed_when_history_returns_false(self, mock_alfred, mock_terminal):
        """DOWN arrow should not be consumed when history handler returns False."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._queue_nav_index = -1
        tui._history_handler = MagicMock()
        tui._history_handler.on_history_down.return_value = False

        result = tui._handle_down_navigation()

        assert result is None


class TestInputListenerReset:
    """Tests for queue navigation reset."""

    def test_reset_queue_nav_clears_state(self, mock_alfred, mock_terminal):
        """Reset should clear queue navigation state."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._queue_nav_index = 2
        tui._queue_draft = "some draft"

        tui._reset_queue_navigation()

        assert tui._queue_nav_index == -1
        assert tui._queue_draft == ""


class TestInputListenerIntegration:
    """Integration tests for the refactored _input_listener."""

    def test_ctrl_key_routing(self, mock_alfred, mock_terminal):
        """Verify control keys are routed to _handle_control_keys."""
        from unittest.mock import patch

        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        with patch.object(tui, '_handle_control_keys', return_value={"consume": True}):
            result = tui._input_listener("\x01")  # Ctrl+A

            assert result == {"consume": True}

    def test_escape_key_routing(self, mock_alfred, mock_terminal):
        """Verify escape key is routed to _handle_escape_key."""
        from unittest.mock import patch

        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        with patch.object(tui, '_handle_control_keys', return_value=None), \
             patch.object(tui, '_handle_escape_key', return_value={"consume": True}) as mock_escape:

            result = tui._input_listener("\x1b")  # Escape character

            assert result == {"consume": True}
            mock_escape.assert_called_once()

    def test_up_arrow_routing_with_queue(self, mock_alfred, mock_terminal):
        """Verify UP arrow routes to _handle_up_navigation when queue exists."""
        from unittest.mock import patch

        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._message_queue = ["msg1"]

        with patch.object(tui, '_handle_control_keys', return_value=None), \
             patch.object(tui, '_handle_escape_key', return_value=None), \
             patch.object(tui, '_get_input_cursor_line', return_value=0), \
             patch.object(tui, '_handle_up_navigation', return_value={"consume": True}) as mock_up:

            result = tui._input_listener("\x1b[A")  # UP arrow sequence

            assert result == {"consume": True}
            mock_up.assert_called_once_with(0)

    def test_down_arrow_routing(self, mock_alfred, mock_terminal):
        """Verify DOWN arrow routes to _handle_down_navigation."""
        from unittest.mock import patch

        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        with patch.object(tui, '_handle_control_keys', return_value=None), \
             patch.object(tui, '_handle_escape_key', return_value=None), \
             patch.object(tui, '_get_input_cursor_line', return_value=0), \
             patch.object(tui, '_handle_up_navigation', return_value=None), \
             patch.object(tui, '_handle_down_navigation', return_value={"consume": True}) as mock_down:

            result = tui._input_listener("\x1b[B")  # DOWN arrow sequence

            assert result == {"consume": True}
            mock_down.assert_called_once()

    def test_other_key_resets_queue_nav(self, mock_alfred, mock_terminal):
        """Verify other keys reset queue navigation."""
        from unittest.mock import patch

        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._queue_nav_index = 1
        tui._queue_draft = "draft"

        with patch.object(tui, '_handle_control_keys', return_value=None), \
             patch.object(tui, '_handle_escape_key', return_value=None), \
             patch.object(tui, '_get_input_cursor_line', return_value=0), \
             patch.object(tui, '_handle_up_navigation', return_value=None), \
             patch.object(tui, '_handle_down_navigation', return_value=None):
            result = tui._input_listener("a")  # Regular key

            assert result is None
            assert tui._queue_nav_index == -1
            assert tui._queue_draft == ""
