"""Tests for CLINotifier toast integration."""

import pytest


class TestCLINotifierToast:
    """Tests for CLINotifier with toast mode (cron job notifications)."""

    @pytest.mark.asyncio
    async def test_cli_notifier_uses_toasts_when_enabled(self):
        """Verify CLINotifier sends toasts when use_toasts=True."""
        from src.cron.notifier import CLINotifier
        from src.interfaces.pypitui.toast import dismiss_all, get_toasts

        dismiss_all()

        notifier = CLINotifier(use_toasts=True)
        await notifier.send("Job completed successfully!")

        toasts = get_toasts()
        assert len(toasts) == 1
        assert "Job completed successfully!" in toasts[0].message
        assert toasts[0].level == "info"

        dismiss_all()

    @pytest.mark.asyncio
    async def test_cli_notifier_uses_stdout_when_toasts_disabled(self):
        """Verify CLINotifier writes to stdout when use_toasts=False."""
        import io

        from src.cron.notifier import CLINotifier

        output = io.StringIO()
        notifier = CLINotifier(output_stream=output, use_toasts=False)
        await notifier.send("Direct output message")

        text = output.getvalue()
        assert "Direct output message" in text
        assert "JOB NOTIFICATION" in text

    @pytest.mark.asyncio
    async def test_alfred_tui_enables_toast_mode(self, mock_alfred, mock_terminal):
        """Verify AlfredTUI enables toast mode on CLINotifier."""
        from src.cron.notifier import CLINotifier
        from src.interfaces.pypitui.tui import AlfredTUI

        # Set up CLINotifier on mock
        mock_alfred.notifier = CLINotifier(use_toasts=False)
        assert mock_alfred.notifier.use_toasts is False

        # Create TUI should enable toast mode
        AlfredTUI(mock_alfred, terminal=mock_terminal)

        assert mock_alfred.notifier.use_toasts is True
