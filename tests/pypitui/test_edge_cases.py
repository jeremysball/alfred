"""Tests for edge cases and polish (Phase 6)."""

import pytest


class TestCleanExit:
    """Tests for clean exit behavior (Phase 6.1)."""

    def test_ctrl_c_sets_running_false(self, mock_alfred, mock_terminal):
        """Verify second Ctrl+C sets running = False."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        assert tui.running is True

        tui._handle_ctrl_c()  # First
        assert tui.running is True

        tui._handle_ctrl_c()  # Second
        assert tui.running is False


class TestEmptyMessageHandling:
    """Tests for empty message handling (Phase 6.2)."""

    def test_empty_message_ignored(self, mock_alfred, mock_terminal):
        """Verify whitespace-only ignored."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        initial_count = len(tui.conversation.children)

        tui._on_submit("   ")  # Whitespace only

        assert len(tui.conversation.children) == initial_count

    def test_message_trimmed(self, mock_alfred, mock_terminal):
        """Verify leading/trailing whitespace stripped."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        tui._on_submit("  hello world  ")

        # Should have created a user message with trimmed content
        assert len(tui.conversation.children) == 1


class TestStreamingErrorHandling:
    """Tests for streaming error handling (Phase 6.4)."""

    @pytest.mark.asyncio
    async def test_streaming_error_shows_in_panel(self, mock_alfred, mock_terminal):
        """Verify error message in assistant panel."""
        from src.interfaces.pypitui.tui import AlfredTUI

        async def error_stream(*args, **kwargs):
            raise RuntimeError("Connection lost")
            yield ""  # pragma: no cover

        mock_alfred.chat_stream = error_stream
        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        await tui._send_message("Hello")

        # Last panel should show error
        last = tui.conversation.children[-1]
        assert last._is_error

    @pytest.mark.asyncio
    async def test_streaming_error_clears_streaming_state(
        self, mock_alfred, mock_terminal
    ):
        """Verify _is_streaming = False even on error."""
        from src.interfaces.pypitui.tui import AlfredTUI

        async def error_stream(*args, **kwargs):
            raise RuntimeError("Test error")
            yield ""  # pragma: no cover

        mock_alfred.chat_stream = error_stream
        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        await tui._send_message("Hello")

        assert tui._is_streaming is False


class TestLongMessages:
    """Tests for long message handling (Phase 6.5)."""

    def test_long_message_wraps(self, mock_alfred, mock_terminal):
        """Verify 500+ char message wraps properly."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        long_text = "x" * 600
        panel = MessagePanel(role="user", content=long_text)

        # Should render without error
        lines = panel.render(width=60)
        text = "".join(lines)
        assert "x" in text

    def test_message_panel_handles_multiline(self, mock_alfred, mock_terminal):
        """Verify newlines preserved."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        multiline = "Line 1\nLine 2\nLine 3"
        panel = MessagePanel(role="user", content=multiline)

        lines = panel.render(width=60)
        text = "".join(lines)
        assert "Line 1" in text
        assert "Line 2" in text
        assert "Line 3" in text


class TestResponsiveStatusLine:
    """Tests for responsive status line (Phase 6.7)."""

    def test_status_full_width(self):
        """Verify all groups shown at 80+ chars."""
        from src.interfaces.pypitui.status_line import StatusLine

        status = StatusLine()
        status.update(
            model="test-model",
            ctx=18000,
            in_tokens=1200,
            out_tokens=449,
            cached=35000,
            reasoning=12,
            queued=0,
        )

        lines = status.render(width=80)
        text = lines[0]

        # All groups should be present
        assert "test-model" in text
        assert "ctx" in text
        assert "in" in text
        assert "out" in text
        assert "cached" in text
        assert "reasoning" in text

    def test_status_compact_width(self):
        """Verify only model + in/out at 40-59 chars."""
        from src.interfaces.pypitui.status_line import StatusLine

        status = StatusLine()
        status.update(
            model="test",
            ctx=18000,
            in_tokens=1200,
            out_tokens=449,
            cached=35000,
            reasoning=12,
            queued=0,
        )

        lines = status.render(width=50)
        text = lines[0]

        # Model and in/out should always be present
        assert "test" in text
        assert "in" in text
        assert "out" in text

    def test_status_shows_queued(self):
        """Verify queued count shown when > 0."""
        from src.interfaces.pypitui.status_line import StatusLine

        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=100,
            out_tokens=50,
            cached=0,
            reasoning=0,
            queued=3,
        )

        lines = status.render(width=80)
        text = lines[0]
        assert "queued 3" in text

    def test_status_hides_queued_when_zero(self):
        """Verify queued hidden when 0."""
        from src.interfaces.pypitui.status_line import StatusLine

        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=100,
            out_tokens=50,
            cached=0,
            reasoning=0,
            queued=0,
        )

        lines = status.render(width=80)
        text = lines[0]
        assert "queued" not in text
