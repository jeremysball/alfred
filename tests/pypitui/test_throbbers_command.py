"""Tests for ThrobbersCommand."""

from unittest.mock import MagicMock, patch

import pytest


class TestThrobbersCommand:
    """Tests for the /throbbers command."""

    @pytest.mark.asyncio
    async def test_command_execute_shows_overlay(self, mock_alfred, mock_terminal):
        """Verify execute shows overlay and starts animation."""
        from alfred.interfaces.pypitui.commands.throbbers import ThrobbersCommand
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        command = ThrobbersCommand()

        # Mock the overlay methods
        with patch.object(tui.tui, 'show_overlay') as mock_show_overlay:
            mock_handle = MagicMock()
            mock_show_overlay.return_value = mock_handle

            # Execute command
            result = command.execute(tui, None)

            # Should return True (handled)
            assert result is True

            # Should show overlay
            mock_show_overlay.assert_called_once()

            # Clean up
            command._close(tui)

    def test_overlay_renders_content(self):
        """Verify ThrobberOverlay renders throbber content."""
        from alfred.interfaces.pypitui.throbber_overlay import ThrobberOverlay

        overlay = ThrobberOverlay(page=0)
        lines = overlay.render(width=60)

        # Should render multiple lines
        assert len(lines) > 0

        # Should contain header
        assert "Throbber" in lines[0]

        # Should contain navigation footer
        assert any("quit" in line.lower() for line in lines)

    def test_overlay_tick_advances_throbbers(self):
        """Verify tick advances throbber animations."""
        from alfred.interfaces.pypitui.throbber_overlay import ThrobberOverlay

        overlay = ThrobberOverlay(page=0)

        # Tick should return True (something changed)
        changed = overlay.tick()

        # Should have changed
        assert changed is True

    @pytest.mark.asyncio
    async def test_command_close_hides_overlay(self, mock_alfred, mock_terminal):
        """Verify close hides overlay and stops animation."""
        from alfred.interfaces.pypitui.commands.throbbers import ThrobbersCommand
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        command = ThrobbersCommand()

        with patch.object(tui.tui, 'show_overlay') as mock_show_overlay:
            mock_handle = MagicMock()
            mock_show_overlay.return_value = mock_handle

            # Execute and then close
            command.execute(tui, None)
            command._close(tui)

            # Should hide the handle
            mock_handle.hide.assert_called_once()

    @pytest.mark.asyncio
    async def test_command_handles_escape_key(self, mock_alfred, mock_terminal):
        """Verify escape key closes overlay."""
        from alfred.interfaces.pypitui.commands.throbbers import ThrobbersCommand
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        command = ThrobbersCommand()

        # Create a mock removal function
        mock_remove = MagicMock()

        with patch.object(tui.tui, 'show_overlay') as mock_show_overlay, \
             patch.object(tui.tui, 'add_input_listener') as mock_add_listener:
            mock_handle = MagicMock()
            mock_show_overlay.return_value = mock_handle
            mock_add_listener.return_value = mock_remove

            # Execute command
            command.execute(tui, None)

            # Verify input listener was added
            assert mock_add_listener.called

            # Simulate escape key by calling the registered listener
            listener = mock_add_listener.call_args[0][0]
            with patch.object(command, '_close') as mock_close:
                result = listener('\x1b')  # ESC character

                # Should consume the input
                assert result == {"consume": True}

            # Clean up
            command._close(tui)

    @pytest.mark.asyncio
    async def test_command_handles_q_key(self, mock_alfred, mock_terminal):
        """Verify 'q' key closes overlay."""
        from alfred.interfaces.pypitui.commands.throbbers import ThrobbersCommand
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        command = ThrobbersCommand()

        mock_remove = MagicMock()

        with patch.object(tui.tui, 'show_overlay') as mock_show_overlay, \
             patch.object(tui.tui, 'add_input_listener') as mock_add_listener:
            mock_handle = MagicMock()
            mock_show_overlay.return_value = mock_handle
            mock_add_listener.return_value = mock_remove

            # Execute command
            command.execute(tui, None)

            # Get the registered listener
            listener = mock_add_listener.call_args[0][0]

            # Simulate 'q' key
            result = listener('q')

            # Should consume the input (and close)
            assert result == {"consume": True}

            # Clean up
            command._close(tui)

    @pytest.mark.asyncio
    async def test_command_input_listener_removed_on_close(self, mock_alfred, mock_terminal):
        """Verify input listener is removed when overlay closes."""
        from alfred.interfaces.pypitui.commands.throbbers import ThrobbersCommand
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        command = ThrobbersCommand()

        mock_remove = MagicMock()

        with patch.object(tui.tui, 'show_overlay') as mock_show_overlay, \
             patch.object(tui.tui, 'add_input_listener') as mock_add_listener:
            mock_handle = MagicMock()
            mock_show_overlay.return_value = mock_handle
            mock_add_listener.return_value = mock_remove

            # Execute command
            command.execute(tui, None)

            # Verify listener was added
            assert mock_add_listener.called

            # Close the overlay
            command._close(tui)

            # Verify removal function was called
            mock_remove.assert_called_once()
