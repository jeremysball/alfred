"""Integration tests for Ctrl+C handling using MockTerminal.

These tests verify the full Ctrl+C behavior end-to-end using MockTerminal
to simulate real terminal input. This ensures the TUI exits cleanly and
doesn't hang.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from pypitui import MockTerminal

if TYPE_CHECKING:
    pass


class TestCtrlCWithMockTerminal:
    """Test Ctrl+C behavior using MockTerminal for end-to-end verification."""

    @pytest.fixture
    def mock_alfred(self) -> MagicMock:
        """Mock Alfred instance for TUI tests."""
        from unittest.mock import AsyncMock

        mock = MagicMock()
        mock.token_tracker.usage.input_tokens = 100
        mock.token_tracker.usage.output_tokens = 50
        mock.token_tracker.usage.cache_read_tokens = 25
        mock.token_tracker.usage.reasoning_tokens = 10
        mock.token_tracker.context_tokens = 200
        mock.model_name = "test-model"
        mock.config.use_markdown_rendering = True
        mock.config.data_dir = Path("/tmp/test")
        mock.core.session_manager.has_active_session.return_value = False
        mock.stop = AsyncMock()  # stop is async
        return mock

    @pytest.fixture
    def mock_terminal(self) -> MockTerminal:
        """Mock terminal for TUI tests."""
        return MockTerminal(cols=80, rows=24)

    @pytest.mark.asyncio
    async def test_ctrl_c_empty_input_exits_immediately(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """Ctrl+C with empty input should exit the run loop immediately."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Send Ctrl+C immediately (no input)
        mock_terminal.queue_input("\x03")

        # Run with timeout to ensure it doesn't hang
        try:
            await asyncio.wait_for(tui.run(), timeout=1.0)
        except TimeoutError:
            pytest.fail(
                "TUI should have exited immediately on Ctrl+C with empty input",
            )

        # Verify TUI stopped cleanly
        assert not tui.running

    @pytest.mark.asyncio
    async def test_ctrl_c_first_clears_input_second_exits(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """First Ctrl+C clears input, second Ctrl+C exits."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Type some text
        mock_terminal.queue_input("hello world")

        # First Ctrl+C - should clear input but not exit
        mock_terminal.queue_input("\x03")

        # Run one iteration to process the input
        # We need to simulate the run loop behavior
        tui.tui.start()

        # Process the typed text
        for _ in "hello world":
            data = mock_terminal.read_sequence(timeout=0.0)
            if data:
                tui.tui.handle_input(data)

        # Process first Ctrl+C
        data = mock_terminal.read_sequence(timeout=0.0)
        if data == "\x03":
            tui._handle_ctrl_c()

        # Should clear input and set pending state
        assert tui.input_field.get_value() == ""
        assert tui._ctrl_c_pending is True
        assert tui.running is True  # Should NOT exit yet

        # Second Ctrl+C - should exit
        mock_terminal.queue_input("\x03")
        data = mock_terminal.read_sequence(timeout=0.0)
        if data == "\x03":
            tui._handle_ctrl_c()

        # Should exit now
        assert not tui.running

        tui.tui.stop()

    @pytest.mark.asyncio
    async def test_ctrl_c_pending_reset_on_other_key(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """Pressing another key after first Ctrl+C should reset pending state."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui.tui.start()

        # Type text
        tui.input_field.set_value("test input")

        # First Ctrl+C - clears input and sets pending
        tui._handle_ctrl_c()
        assert tui._ctrl_c_pending is True
        assert tui.input_field.get_value() == ""

        # Type a new character - should reset pending
        tui.input_field.set_value("n")
        tui._reset_ctrl_c_state()

        assert tui._ctrl_c_pending is False

        # Now Ctrl+C should clear input again, not exit
        tui._handle_ctrl_c()
        assert tui.input_field.get_value() == ""
        assert tui._ctrl_c_pending is True
        assert tui.running is True  # Still running

        tui.tui.stop()

    @pytest.mark.asyncio
    async def test_tui_cleanup_on_exit(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """Verify TUI calls stop() and cleans up properly on exit."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Mock the tui.start/stop to track calls
        with (
            patch.object(tui.tui, 'start') as mock_start,
            patch.object(tui.tui, 'stop') as mock_stop,
            patch.object(tui.tui, 'render_frame') as mock_render,
        ):
            mock_start.return_value = None
            mock_stop.return_value = None
            mock_render.return_value = None

            # Feed Ctrl+C to exit immediately
            mock_terminal.queue_input("\x03")

            with suppress(TimeoutError):
                await asyncio.wait_for(tui.run(), timeout=1.0)

            # Verify cleanup was called
            mock_start.assert_called_once()
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_ctrl_c_while_streaming_exits_cleanly(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """Ctrl+C should exit cleanly even when streaming is active."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Simulate streaming state
        tui._is_streaming = True
        tui._is_sending = True

        # Feed Ctrl+C
        mock_terminal.queue_input("\x03")

        try:
            await asyncio.wait_for(tui.run(), timeout=1.0)
        except TimeoutError:
            pytest.fail("TUI should exit even while streaming")

        assert not tui.running


class TestCtrlCStateMachine:
    """Test Ctrl+C as a state machine with various transitions."""

    @pytest.fixture
    def mock_alfred(self) -> MagicMock:
        """Mock Alfred instance."""
        from unittest.mock import AsyncMock

        mock = MagicMock()
        mock.token_tracker.usage.input_tokens = 0
        mock.token_tracker.usage.output_tokens = 0
        mock.token_tracker.usage.cache_read_tokens = 0
        mock.token_tracker.usage.reasoning_tokens = 0
        mock.token_tracker.context_tokens = 0
        mock.model_name = "test-model"
        mock.config.use_markdown_rendering = True
        mock.config.data_dir = Path("/tmp/test")
        mock.core.session_manager.has_active_session.return_value = False
        mock.stop = AsyncMock()
        return mock

    @pytest.fixture
    def mock_terminal(self) -> MockTerminal:
        """Mock terminal."""
        return MockTerminal(cols=80, rows=24)

    def test_state_transition_empty_to_exit(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """State: empty input -> Ctrl+C -> exit."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui.tui.start()

        # Initial state
        assert tui.input_field.get_value() == ""
        assert not tui._ctrl_c_pending
        assert tui.running

        # Ctrl+C on empty input
        tui._handle_ctrl_c()

        # Final state - should exit immediately without setting pending
        assert not tui.running
        assert not tui._ctrl_c_pending  # Not set when exiting immediately

        tui.tui.stop()

    def test_state_transition_input_to_clear_to_exit(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """State: has input -> Ctrl+C (clear) -> Ctrl+C (exit)."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui.tui.start()

        # Initial state with input
        tui.input_field.set_value("some text")
        assert tui.input_field.get_value() == "some text"
        assert not tui._ctrl_c_pending
        assert tui.running

        # First Ctrl+C - clear input
        tui._handle_ctrl_c()

        assert tui.input_field.get_value() == ""
        assert tui._ctrl_c_pending
        assert tui.running  # Still running

        # Second Ctrl+C - exit
        tui._handle_ctrl_c()

        assert not tui.running

        tui.tui.stop()

    def test_state_transition_clear_on_type(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """State: pending -> type character -> reset -> clear again."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui.tui.start()

        # Setup: have input, first Ctrl+C clears it
        tui.input_field.set_value("original")
        tui._handle_ctrl_c()
        assert tui._ctrl_c_pending

        # Type something (triggers reset)
        tui._reset_ctrl_c_state()
        tui.input_field.set_value("new text")

        assert not tui._ctrl_c_pending

        # Ctrl+C should clear, not exit
        tui._handle_ctrl_c()
        assert tui.input_field.get_value() == ""
        assert tui._ctrl_c_pending
        assert tui.running

        tui.tui.stop()


class TestCtrlCEdgeCases:
    """Edge cases and error handling for Ctrl+C."""

    @pytest.fixture
    def mock_alfred(self) -> MagicMock:
        """Mock Alfred instance."""
        from unittest.mock import AsyncMock

        mock = MagicMock()
        mock.token_tracker.usage.input_tokens = 0
        mock.token_tracker.usage.output_tokens = 0
        mock.token_tracker.usage.cache_read_tokens = 0
        mock.token_tracker.usage.reasoning_tokens = 0
        mock.token_tracker.context_tokens = 0
        mock.model_name = "test-model"
        mock.config.use_markdown_rendering = True
        mock.config.data_dir = Path("/tmp/test")
        mock.core.session_manager.has_active_session.return_value = False
        mock.stop = AsyncMock()
        return mock

    @pytest.fixture
    def mock_terminal(self) -> MockTerminal:
        """Mock terminal."""
        return MockTerminal(cols=80, rows=24)

    def test_ctrl_c_whitespace_only_input(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """Ctrl+C with only whitespace should exit immediately."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui.tui.start()

        # Only whitespace
        tui.input_field.set_value("   \t\n  ")

        # Should exit immediately (treated as empty)
        tui._handle_ctrl_c()

        assert not tui.running

        tui.tui.stop()

    def test_rapid_ctrl_c_presses(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """Multiple rapid Ctrl+C presses should still work correctly."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui.tui.start()

        tui.input_field.set_value("text")

        # First Ctrl+C - clear
        tui._handle_ctrl_c()
        assert tui.input_field.get_value() == ""
        assert tui._ctrl_c_pending
        assert tui.running

        # Multiple Ctrl+C presses while pending
        tui._handle_ctrl_c()
        assert not tui.running  # Should exit on second

        tui.tui.stop()

    def test_ctrl_c_after_submission(
        self,
        mock_alfred: MagicMock,
        mock_terminal: MockTerminal,
    ) -> None:
        """Ctrl+C after message submission should exit (empty input)."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui.tui.start()

        # Simulate submitted message (input cleared)
        tui.input_field.set_value("")
        tui._ctrl_c_pending = False

        # Should exit immediately
        tui._handle_ctrl_c()

        assert not tui.running

        tui.tui.stop()
