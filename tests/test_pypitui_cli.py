"""Tests for PyPiTUI-based CLI interface."""

from collections.abc import AsyncIterator
from unittest.mock import Mock

import pytest
from pypitui import MockTerminal

from src.alfred import Alfred


@pytest.fixture
def mock_terminal():
    """Create a MockTerminal for testing."""
    return MockTerminal()


@pytest.fixture
def mock_alfred():
    """Create a mock Alfred instance with async chat_stream."""
    alfred = Mock(spec=Alfred)

    # Create an async generator for chat_stream
    async def async_chat_stream(*args, **kwargs) -> AsyncIterator[str]:
        chunks = ["Hello", " ", "world", "!"]
        for chunk in chunks:
            yield chunk

    alfred.chat_stream = async_chat_stream
    return alfred


class TestAlfredTUIInitialization:
    """Tests for AlfredTUI class initialization."""

    def test_alfred_tui_init_creates_components(self, mock_alfred, mock_terminal):
        """Verify __init__ creates conversation, status_line, input_field."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        assert tui.conversation is not None
        assert tui.status_line is not None
        assert tui.input_field is not None

    def test_alfred_tui_has_tui_instance(self, mock_alfred, mock_terminal):
        """Verify single TUI instance exists."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        assert tui.tui is not None

    def test_alfred_tui_never_clears(self, mock_alfred, mock_terminal):
        """Verify AlfredTUI class has no clear method - we never clear screen."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # AlfredTUI should not have a clear method (we never clear for scrollback)
        assert not hasattr(tui, "clear")

    def test_alfred_tui_stores_alfred_reference(self, mock_alfred, mock_terminal):
        """Verify Alfred instance is stored."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        assert tui.alfred is mock_alfred
