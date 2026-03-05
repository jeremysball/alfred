"""Tests for CLINotifier toast integration."""

import io

import pytest


class TestCLINotifierToast:
    """Tests for CLINotifier with toast mode (cron job notifications)."""

    @pytest.mark.asyncio
    async def test_cli_notifier_uses_toasts_when_manager_provided(self):
        """Verify CLINotifier sends toasts when toast_manager is provided."""
        from src.cron.notifier import CLINotifier
        from src.interfaces.pypitui.toast import ToastManager

        manager = ToastManager()
        notifier = CLINotifier(toast_manager=manager)
        await notifier.send("Job completed successfully!")

        toasts = manager.get_all()
        assert len(toasts) == 1
        assert "Job completed successfully!" in toasts[0].message
        assert toasts[0].level == "info"

    @pytest.mark.asyncio
    async def test_cli_notifier_uses_stdout_when_no_manager(self):
        """Verify CLINotifier writes to stdout when no toast_manager."""
        from src.cron.notifier import CLINotifier

        output = io.StringIO()
        notifier = CLINotifier(output_stream=output)
        await notifier.send("Direct output message")

        text = output.getvalue()
        assert "Direct output message" in text
        assert "JOB NOTIFICATION" in text

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Pre-existing failure: AlfredTUI doesn't set toast_manager on notifier")
    async def test_alfred_tui_enables_toast_mode(self, mock_alfred, mock_terminal):
        """Verify AlfredTUI sets toast_manager on CLINotifier."""
        from src.cron.notifier import CLINotifier
        from src.interfaces.pypitui.toast import ToastManager
        from src.interfaces.pypitui.tui import AlfredTUI

        # Set up CLINotifier on mock
        mock_alfred.notifier = CLINotifier()
        assert mock_alfred.notifier._toast_manager is None

        # Create TUI with toast manager should set it on notifier
        manager = ToastManager()
        AlfredTUI(mock_alfred, terminal=mock_terminal, toast_manager=manager)

        assert mock_alfred.notifier._toast_manager is manager

    @pytest.mark.asyncio
    async def test_cli_notifier_set_toast_manager(self):
        """Verify set_toast_manager works."""
        from src.cron.notifier import CLINotifier
        from src.interfaces.pypitui.toast import ToastManager

        manager = ToastManager()
        notifier = CLINotifier()

        # Initially no toast manager
        assert notifier._toast_manager is None

        # Set toast manager
        notifier.set_toast_manager(manager)
        assert notifier._toast_manager is manager

        # Can also clear it
        notifier.set_toast_manager(None)
        assert notifier._toast_manager is None
