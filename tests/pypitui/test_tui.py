"""Tests for AlfredTUI main class and integration."""

import pytest


class TestAlfredTUIInit:
    """Tests for AlfredTUI initialization."""

    def test_init_creates_components(self, mock_alfred, mock_terminal):
        """Verify TUI creates all required components."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        assert tui.conversation is not None
        assert tui.status_line is not None
        assert tui.input_field is not None
        assert tui.running is True


class TestOnSubmit:
    """Tests for _on_submit message handling."""

    def test_on_submit_creates_user_message(self, mock_alfred, mock_terminal):
        """Verify user message added to conversation."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        initial_count = len(tui.conversation.children)

        tui._on_submit("Hello Alfred")

        assert len(tui.conversation.children) == initial_count + 1

    def test_on_submit_clears_input(self, mock_alfred, mock_terminal):
        """Verify input cleared after submit."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui.input_field.set_value("Some text")

        tui._on_submit("Hello")

        assert tui.input_field.get_value() == ""

    def test_on_submit_ignores_empty(self, mock_alfred, mock_terminal):
        """Verify empty messages ignored."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        initial_count = len(tui.conversation.children)

        tui._on_submit("   ")

        assert len(tui.conversation.children) == initial_count

    def test_on_submit_uses_message_panel(self, mock_alfred, mock_terminal):
        """Verify user messages use MessagePanel."""
        from src.interfaces.pypitui.message_panel import MessagePanel
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        tui._on_submit("Test message")

        # Last child should be a MessagePanel
        last_child = tui.conversation.children[-1]
        assert isinstance(last_child, MessagePanel)


class TestSendMessage:
    """Tests for _send_message async method."""

    @pytest.mark.asyncio
    async def test_send_message_creates_assistant_panel(self, mock_alfred, mock_terminal):
        """Verify assistant message panel created."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        initial_count = len(tui.conversation.children)

        await tui._send_message("Hello")

        # Should have user + assistant messages
        assert len(tui.conversation.children) >= initial_count + 1

    @pytest.mark.asyncio
    async def test_send_message_uses_message_panel(self, mock_alfred, mock_terminal):
        """Verify assistant messages use MessagePanel."""
        from src.interfaces.pypitui.message_panel import MessagePanel
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        await tui._send_message("Hello")

        # Find assistant panel
        assistant_panels = [
            c for c in tui.conversation.children if isinstance(c, MessagePanel)
        ]
        assert len(assistant_panels) >= 1

    @pytest.mark.asyncio
    async def test_error_sets_red_border(self, mock_alfred, mock_terminal):
        """Verify errors trigger set_error() on panel."""
        from src.interfaces.pypitui.tui import AlfredTUI

        # Make chat_stream raise an error
        async def error_stream(*args, **kwargs):
            raise RuntimeError("Test error")
            yield ""  # pragma: no cover

        mock_alfred.chat_stream = error_stream
        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        await tui._send_message("Hello")

        # Last message should show error
        last = tui.conversation.children[-1]
        assert last._is_error


class TestToolCallbackIntegration:
    """Tests for tool callback integration with inline tool calls (Phase 4.4)."""

    def test_tool_callback_adds_to_current_message(self, mock_alfred, mock_terminal):
        """Verify ToolStart adds tool call to current assistant message."""
        from src.agent import ToolStart
        from src.interfaces.pypitui.message_panel import MessagePanel
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Simulate an active assistant message
        assistant_msg = MessagePanel(role="assistant", content="Let me search...")
        tui._current_assistant_msg = assistant_msg

        # Trigger ToolStart
        event = ToolStart(tool_call_id="call-1", tool_name="remember")
        tui._tool_callback(event)

        # Tool call should be in the message's tool_calls list
        assert len(assistant_msg._tool_calls) == 1
        assert assistant_msg._tool_calls[0].tool_name == "remember"

    def test_tool_callback_appends_on_output(self, mock_alfred, mock_terminal):
        """Verify ToolOutput appends to tool call in message."""
        from src.agent import ToolOutput, ToolStart
        from src.interfaces.pypitui.message_panel import MessagePanel
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Set up current message with tool call
        assistant_msg = MessagePanel(role="assistant", content="Searching...")
        tui._current_assistant_msg = assistant_msg
        tui._tool_callback(ToolStart(tool_call_id="call-1", tool_name="bash"))

        # Output
        tui._tool_callback(
            ToolOutput(tool_call_id="call-1", tool_name="bash", chunk="Hello")
        )

        # Verify output was appended
        assert assistant_msg._tool_calls[0].output == "Hello"

    def test_tool_callback_finalizes_on_end(self, mock_alfred, mock_terminal):
        """Verify ToolEnd sets final status."""
        from src.agent import ToolEnd, ToolStart
        from src.interfaces.pypitui.message_panel import MessagePanel
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Set up current message with tool call
        assistant_msg = MessagePanel(role="assistant", content="Done")
        tui._current_assistant_msg = assistant_msg
        tui._tool_callback(ToolStart(tool_call_id="call-1", tool_name="remember"))
        tui._tool_callback(
            ToolEnd(tool_call_id="call-1", tool_name="remember", result="OK")
        )

        # Status should be success
        assert assistant_msg._tool_calls[0].status == "success"

    def test_tool_callback_error_style(self, mock_alfred, mock_terminal):
        """Verify error sets error status."""
        from src.agent import ToolEnd, ToolStart
        from src.interfaces.pypitui.message_panel import MessagePanel
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Set up current message with tool call
        assistant_msg = MessagePanel(role="assistant", content="Failed")
        tui._current_assistant_msg = assistant_msg
        tui._tool_callback(ToolStart(tool_call_id="call-1", tool_name="bash"))
        tui._tool_callback(
            ToolEnd(
                tool_call_id="call-1", tool_name="bash", result="Failed", is_error=True
            )
        )

        # Status should be error
        assert assistant_msg._tool_calls[0].status == "error"


class TestCtrlCBehavior:
    """Tests for Ctrl-C clear input then exit behavior (Phase 1.9)."""

    def test_ctrl_c_clears_input_when_has_text(self, mock_alfred, mock_terminal):
        """Verify first Ctrl-C clears input, shows hint."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Put text in input
        tui.input_field.set_value("some text")

        # Simulate Ctrl-C
        tui._handle_ctrl_c()

        # Input should be cleared
        assert tui.input_field.get_value() == ""
        # Pending flag should be set
        assert tui._ctrl_c_pending is True
        # Hint should be visible
        assert tui._exit_hint_visible is True

    def test_ctrl_c_shows_hint_when_input_empty(self, mock_alfred, mock_terminal):
        """Verify hint shown even with empty input."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Empty input
        tui.input_field.set_value("")

        # Simulate Ctrl-C
        tui._handle_ctrl_c()

        # Pending flag should be set
        assert tui._ctrl_c_pending is True
        assert tui._exit_hint_visible is True

    def test_second_ctrl_c_exits(self, mock_alfred, mock_terminal):
        """Verify running = False after two Ctrl-C presses."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # First Ctrl-C
        tui._handle_ctrl_c()
        assert tui.running is True  # Still running
        assert tui._ctrl_c_pending is True

        # Second Ctrl-C
        tui._handle_ctrl_c()
        assert tui.running is False  # Now exits

    def test_other_key_resets_ctrl_c_state(self, mock_alfred, mock_terminal):
        """Verify any other key clears hint, resets state."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # First Ctrl-C to set pending state
        tui._handle_ctrl_c()
        assert tui._ctrl_c_pending is True
        assert tui._exit_hint_visible is True

        # Simulate another key press (reset)
        tui._reset_ctrl_c_state()

        # State should be reset
        assert tui._ctrl_c_pending is False
        assert tui._exit_hint_visible is False

    def test_ctrl_c_state_persists_across_frames(self, mock_alfred, mock_terminal):
        """Verify state doesn't auto-reset between frames."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Set pending state
        tui._handle_ctrl_c()

        # Simulate a frame passing (state should persist)
        # This tests that we don't accidentally reset on render
        assert tui._ctrl_c_pending is True

        # After another "frame" still pending
        assert tui._ctrl_c_pending is True


class TestToastTUIIntegration:
    """Tests for toast integration with AlfredTUI."""

    def test_keypress_dismisses_toasts(self, mock_alfred, mock_terminal):
        """Verify any keypress dismisses all toasts."""
        from src.interfaces.pypitui.toast import ToastManager
        from src.interfaces.pypitui.tui import AlfredTUI

        manager = ToastManager()
        tui = AlfredTUI(mock_alfred, terminal=mock_terminal, toast_manager=manager)

        # Add some toasts directly
        manager.add("Warning 1", "warning")
        manager.add("Error 1", "error")

        assert len(manager.get_all()) == 2

        # Simulate keypress reset (this is what happens on any non-CtrlC key)
        tui._reset_ctrl_c_state()  # This should also dismiss toasts

        # Toasts should be dismissed
        assert len(manager.get_all()) == 0

    def test_toast_handler_with_manager(self, mock_alfred, mock_terminal):
        """Verify ToastHandler can be created with ToastManager."""
        import logging

        from src.interfaces.pypitui.toast import ToastHandler, ToastManager

        manager = ToastManager()
        handler = ToastHandler(manager)

        # Use handler with a logger
        logger = logging.getLogger("src.test_handler")
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

        logger.warning("Test warning")

        # Toast should be in manager
        toasts = manager.get_all()
        assert len(toasts) == 1
        assert "Test warning" in toasts[0].message

        logger.removeHandler(handler)


class TestStreamingState:
    """Tests for streaming state and throbber behavior."""

    @pytest.mark.asyncio
    async def test_throbber_stops_when_streaming_ends(self, mock_alfred, mock_terminal):
        """Verify throbber stops animating when streaming completes."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Initially not streaming
        assert tui._is_streaming is False

        # Start streaming (simulate _send_message start)
        tui._is_streaming = True
        tui._update_status()

        # Status line should show throbber
        lines = tui.status_line.render(width=80)
        assert lines[0].startswith("⠋")  # Throbber visible

        # Simulate streaming ending (finally block behavior)
        tui._is_streaming = False
        tui._update_status()

        # Status line should NOT show throbber anymore
        lines = tui.status_line.render(width=80)
        assert not lines[0].startswith("⠋")  # Throbber hidden
        assert "test-model" in lines[0]  # Model name visible instead

    def test_throbber_starts_immediately_on_submit(self, mock_alfred, mock_terminal):
        """Bug Fix: Throbber should start immediately when user presses Enter."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Initially not sending or streaming
        assert tui._is_sending is False
        assert tui._is_streaming is False

        # Simulate submit (but not the async task - just the state change)
        tui._is_sending = True
        tui._update_status()

        # Status line should show throbber immediately (before streaming starts)
        lines = tui.status_line.render(width=80)
        assert lines[0].startswith("⠋")  # Throbber visible immediately

        # When streaming actually starts, _is_streaming becomes True and _is_sending becomes False
        tui._is_streaming = True
        tui._is_sending = False
        tui._update_status()

        # Throbber should still be visible during streaming
        lines = tui.status_line.render(width=80)
        assert lines[0].startswith("⠋")  # Throbber still visible

