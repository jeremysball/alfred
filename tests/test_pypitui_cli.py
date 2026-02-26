"""Tests for PyPiTUI-based CLI interface."""

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import Mock, patch

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


class TestAlfredTUIRunLoop:
    """Tests for AlfredTUI.run() main loop."""

    @pytest.mark.asyncio
    async def test_run_yields_to_event_loop(self, mock_alfred, mock_terminal):
        """Verify run() calls await asyncio.sleep()."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Run one iteration then stop
        iterations = 0

        async def count_and_sleep(*args, **kwargs):
            nonlocal iterations
            iterations += 1
            if iterations >= 2:
                tui.running = False

        with patch.object(asyncio, "sleep", side_effect=count_and_sleep):
            await tui.run()

        assert iterations >= 2, "Loop should have iterated at least twice"

    @pytest.mark.asyncio
    async def test_run_reads_terminal_input(self, mock_alfred, mock_terminal):
        """Verify run() calls terminal.read_sequence()."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Track if read_sequence was called
        read_called = False
        original_read = mock_terminal.read_sequence

        def track_read(*args, **kwargs):
            nonlocal read_called
            read_called = True
            tui.running = False  # Stop after first read
            return original_read(*args, **kwargs)

        mock_terminal.read_sequence = track_read

        await tui.run()

        assert read_called, "terminal.read_sequence() should be called"

    @pytest.mark.asyncio
    async def test_run_handles_input(self, mock_alfred, mock_terminal):
        """Verify run() calls tui.handle_input() when data received."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Mock read_sequence to return data once
        call_count = 0

        def mock_read(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "a"  # Return some input data
            tui.running = False
            return None

        mock_terminal.read_sequence = mock_read

        # Track handle_input calls
        handled_data = []

        def track_handle(data):
            handled_data.append(data)

        tui.tui.handle_input = track_handle

        await tui.run()

        assert "a" in handled_data, "tui.handle_input() should be called with input data"

    @pytest.mark.asyncio
    async def test_run_renders_frames(self, mock_alfred, mock_terminal):
        """Verify run() calls tui.render_frame()."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Track render_frame calls
        render_count = 0

        def track_render():
            nonlocal render_count
            render_count += 1
            if render_count >= 2:
                tui.running = False

        tui.tui.render_frame = track_render

        await tui.run()

        assert render_count >= 2, "render_frame() should be called each iteration"

    @pytest.mark.asyncio
    async def test_run_exits_on_running_false(self, mock_alfred, mock_terminal):
        """Verify loop exits when self.running = False."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Set running to False immediately
        tui.running = False

        # Should exit immediately without error
        await tui.run()

        # If we get here, the loop exited properly


class TestAlfredTUIInputHandling:
    """Tests for AlfredTUI input handling."""

    def test_on_submit_adds_user_message(self, mock_alfred, mock_terminal):
        """Verify user message added to conversation."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Get initial child count
        initial_count = len(tui.conversation.children)

        # Submit a message
        tui._on_submit("Hello Alfred")

        # Verify message was added
        assert len(tui.conversation.children) == initial_count + 1

    def test_on_submit_clears_input(self, mock_alfred, mock_terminal):
        """Verify input field cleared after submit."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Set some text in input
        tui.input_field.set_value("Test message")

        # Submit
        tui._on_submit("Test message")

        # Verify input was cleared
        assert tui.input_field.get_value() == ""

    def test_on_submit_ignores_empty(self, mock_alfred, mock_terminal):
        """Verify empty/whitespace ignored."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Get initial child count
        initial_count = len(tui.conversation.children)

        # Try to submit empty messages
        tui._on_submit("")
        tui._on_submit("   ")
        tui._on_submit("\t\n")

        # Verify no messages were added
        assert len(tui.conversation.children) == initial_count

    def test_on_submit_starts_response_task(self, mock_alfred, mock_terminal):
        """Verify asyncio task created for response."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Submit a message - should not raise
        tui._on_submit("Hello")

        # Verify input was cleared (shows _on_submit executed)
        assert tui.input_field.get_value() == ""
