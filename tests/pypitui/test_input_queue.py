"""Tests for input queue functionality (Phase 5)."""

import pytest


class TestInputQueue:
    """Tests for message queue during streaming (Phase 5.1)."""

    def test_queue_empty_on_init(self, mock_alfred, mock_terminal):
        """Verify queue starts empty."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        assert tui._message_queue == []
        assert tui._is_streaming is False

    def test_queue_message_during_streaming(self, mock_alfred, mock_terminal):
        """Verify message queued when streaming."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._is_streaming = True

        tui._on_submit("Queued message")

        # Should be queued, not sent immediately
        assert len(tui._message_queue) == 1
        assert tui._message_queue[0] == "Queued message"

    @pytest.mark.asyncio
    async def test_queue_processed_after_stream(self, mock_alfred, mock_terminal):
        """Verify queued messages sent after stream ends."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Queue a message
        tui._message_queue.append("Follow-up message")

        # End of stream should process queue
        await tui._send_message("First message")

        # Queue should be empty (message was sent)
        assert len(tui._message_queue) == 0

    @pytest.mark.asyncio
    async def test_queue_multiple_messages(self, mock_alfred, mock_terminal):
        """Verify multiple messages queue and send in order."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Queue multiple messages
        tui._message_queue.extend(["Second", "Third"])

        await tui._send_message("First")

        # First in queue should have been sent
        assert len(tui._message_queue) == 1
        assert tui._message_queue[0] == "Third"


class TestQueueStatusIndicator:
    """Tests for status line queue indicator (Phase 5.2)."""

    def test_status_line_shows_queue_count(self, mock_alfred, mock_terminal):
        """Verify 'queued:2' appears in status line."""
        from src.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)
        tui._is_streaming = True

        # Queue messages
        tui._on_submit("Message 1")
        tui._on_submit("Message 2")

        # Status line should show queue count
        lines = tui.status_line.render(width=80)
        text = lines[0]
        assert "queued 2" in text or "queued:2" in text
