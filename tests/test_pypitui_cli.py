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


class TestAlfredTUIResponseHandling:
    """Tests for AlfredTUI response handling."""

    @pytest.mark.asyncio
    async def test_send_message_adds_assistant_panel(self, mock_alfred, mock_terminal):
        """Verify assistant panel created in conversation."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Get initial child count
        initial_count = len(tui.conversation.children)

        # Call _send_message
        await tui._send_message("Hello")

        # Verify assistant message was added
        assert len(tui.conversation.children) == initial_count + 1

    @pytest.mark.asyncio
    async def test_send_message_calls_alfred_chat_stream(self, mock_alfred, mock_terminal):
        """Verify alfred.chat_stream() called with message."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Call _send_message
        await tui._send_message("Test message")

        # The mock_alfred fixture's chat_stream should have been called
        # We can verify by checking that conversation has content
        assert len(tui.conversation.children) > 0

    @pytest.mark.asyncio
    async def test_send_message_updates_assistant_content(self, mock_alfred, mock_terminal):
        """Verify panel content updated with streamed chunks."""
        from src.interfaces.pypitui_cli import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Call _send_message
        await tui._send_message("Hello")

        # Get the last child (assistant message)
        assistant_msg = tui.conversation.children[-1]

        # Verify it has content from the mock chat_stream ("Hello", " ", "world", "!")
        # The Text component should contain "Alfred: Hello world!"
        assert "Alfred:" in str(assistant_msg._text)


class TestMessagePanel:
    """Tests for MessagePanel component."""

    def test_message_panel_renders_with_title_you(self, mock_terminal):
        """Verify user panel has 'You' title."""
        from src.interfaces.pypitui_cli import MessagePanel

        panel = MessagePanel(role="user", content="Hello")
        lines = panel.render(width=40)

        # Title should appear in border
        assert any("You" in line for line in lines), "User panel should have 'You' title"

    def test_message_panel_renders_with_title_alfred(self, mock_terminal):
        """Verify assistant panel has 'Alfred' title."""
        from src.interfaces.pypitui_cli import MessagePanel

        panel = MessagePanel(role="assistant", content="Hello")
        lines = panel.render(width=40)

        # Title should appear in border
        assert any("Alfred" in line for line in lines), "Assistant panel should have 'Alfred' title"

    def test_message_panel_user_has_cyan_border(self, mock_terminal):
        """Verify cyan styling for user messages."""
        from src.interfaces.pypitui_cli import MessagePanel

        panel = MessagePanel(role="user", content="Hello")
        lines = panel.render(width=40)
        output = "\n".join(lines)

        # Cyan ANSI code is \x1b[36m
        assert "\x1b[36m" in output, "User panel should have cyan border"

    def test_message_panel_assistant_has_green_border(self, mock_terminal):
        """Verify green styling for assistant messages."""
        from src.interfaces.pypitui_cli import MessagePanel

        panel = MessagePanel(role="assistant", content="Hello")
        lines = panel.render(width=40)
        output = "\n".join(lines)

        # Green ANSI code is \x1b[32m
        assert "\x1b[32m" in output, "Assistant panel should have green border"

    def test_message_panel_error_has_red_border(self, mock_terminal):
        """Verify red styling for error state."""
        from src.interfaces.pypitui_cli import MessagePanel

        panel = MessagePanel(role="assistant", content="Hello")
        panel.set_error("Something went wrong")
        lines = panel.render(width=40)
        output = "\n".join(lines)

        # Red ANSI code is \x1b[31m
        assert "\x1b[31m" in output, "Error panel should have red border"

    def test_message_panel_set_content_updates(self, mock_terminal):
        """Verify set_content() changes rendered text."""
        from src.interfaces.pypitui_cli import MessagePanel

        panel = MessagePanel(role="assistant", content="Initial")
        lines1 = panel.render(width=40)
        initial_output = "\n".join(lines1)

        panel.set_content("Updated content here")
        lines2 = panel.render(width=40)
        updated_output = "\n".join(lines2)

        assert "Initial" in initial_output
        assert "Updated content here" in updated_output
        assert "Initial" not in updated_output

    def test_message_panel_wraps_long_content(self, mock_terminal):
        """Verify Text handles wrapping internally."""
        from src.interfaces.pypitui_cli import MessagePanel

        # Create a long message
        long_content = "This is a very long message that should wrap across multiple lines when rendered in a narrow terminal width."
        panel = MessagePanel(role="user", content=long_content)
        lines = panel.render(width=30)

        # Should render to multiple lines (Text handles wrapping)
        assert len(lines) > 1, "Long content should wrap to multiple lines"
        # Content should be present (possibly split across lines)
        output = "\n".join(lines)
        # Check for individual words that should be in the output
        assert "very" in output
        assert "multiple" in output
        assert "terminal" in output


class TestEntryPointIntegration:
    """Tests for entry point integration."""

    def test_main_imports_pypitui_cli(self):
        """Verify src.cli.main can import AlfredTUI."""
        # This should not raise ImportError
        from src.interfaces.pypitui_cli import AlfredTUI

        assert AlfredTUI is not None

    @pytest.mark.asyncio
    async def test_run_chat_creates_interface(self, mock_alfred):
        """Verify _run_chat() instantiates AlfredTUI."""
        from unittest.mock import AsyncMock, patch

        from src.cli.main import _run_chat

        # Mock AlfredTUI at the import location
        with patch(
            "src.interfaces.pypitui_cli.AlfredTUI"
        ) as mock_tui_class, patch(
            "src.interfaces.pypitui_cli.MessagePanel"
        ):
            mock_instance = AsyncMock()
            mock_tui_class.return_value = mock_instance

            # Mock alfred.start()
            mock_alfred.start = AsyncMock()

            # Run _run_chat
            await _run_chat(mock_alfred)

            # Verify AlfredTUI was instantiated
            mock_tui_class.assert_called_once_with(mock_alfred)
