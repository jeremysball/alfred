"""Tests for CLINotifier toast notifications."""

import pytest

from alfred.cron.notifier import CLINotifier
from alfred.interfaces.pypitui.toast import ToastHandler, ToastManager


class TestCLINotifierToasts:
    """Test that CLINotifier sends toasts immediately."""

    @pytest.mark.asyncio
    async def test_cli_notifier_sends_toasts_immediately(self):
        """Toasts are always added immediately (no deferment)."""
        manager = ToastManager()
        notifier = CLINotifier(toast_manager=manager)

        await notifier.send("Test message")

        # Toast should be added immediately
        toasts = manager.get_all()
        assert len(toasts) == 1
        assert "Test message" in toasts[0].message

    @pytest.mark.asyncio
    async def test_cli_notifier_respects_max_visible_toasts(self):
        """Only MAX_VISIBLE_TOASTS are kept (most recent)."""
        from alfred.interfaces.pypitui.toast import MAX_VISIBLE_TOASTS

        manager = ToastManager()
        notifier = CLINotifier(toast_manager=manager)

        # Add more than MAX_VISIBLE_TOASTS
        for i in range(MAX_VISIBLE_TOASTS + 3):
            await notifier.send(f"Message {i}")

        # Should only keep most recent MAX_VISIBLE_TOASTS
        toasts = manager.get_all()
        assert len(toasts) == MAX_VISIBLE_TOASTS
        # Oldest messages should be trimmed
        assert "Message 0" not in [t.message for t in toasts]
        # Most recent should be kept
        assert f"Message {MAX_VISIBLE_TOASTS + 2}" in [t.message for t in toasts]


class TestToastHandler:
    """Test that ToastHandler creates toasts from logs."""

    def test_toast_handler_creates_toasts_from_src_modules(self):
        """Create toasts from alfred.* module logs immediately."""
        import logging

        manager = ToastManager()
        handler = ToastHandler(manager)

        # Create a WARNING level log record from alfred.* module
        record = logging.LogRecord(
            name="src.cron.scheduler",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Test warning",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Toast should be added immediately
        toasts = manager.get_all()
        assert len(toasts) == 1
        assert "Test warning" in toasts[0].message

    def test_toast_handler_skips_non_src_modules(self):
        """Don't create toasts from non-src modules."""
        import logging

        manager = ToastManager()
        handler = ToastHandler(manager)

        # Create a log record from a non-src module
        record = logging.LogRecord(
            name="some.other.module",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Test warning from other module",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Toast should NOT be added (not from alfred.*)
        toasts = manager.get_all()
        assert len(toasts) == 0

    def test_toast_handler_maps_log_levels_correctly(self):
        """Map Python log levels to toast levels correctly."""
        import logging

        manager = ToastManager()
        handler = ToastHandler(manager)

        # ERROR -> error
        error_record = logging.LogRecord(
            name="src.test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        handler.emit(error_record)

        # WARNING -> warning
        warning_record = logging.LogRecord(
            name="src.test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        handler.emit(warning_record)

        toasts = manager.get_all()
        assert len(toasts) == 2
        assert toasts[0].level == "error"
        assert toasts[1].level == "warning"
