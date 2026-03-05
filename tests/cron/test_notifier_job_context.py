"""Tests for CLINotifier job context detection and toast deferral."""

import io

import pytest

from src.cron.notifier import CLINotifier
from src.interfaces.pypitui.toast import ToastHandler, ToastManager


class TestCLINotifierJobContext:
    """Test that CLINotifier defers toasts during job execution."""

    @pytest.mark.asyncio
    async def test_cli_notifier_defers_toasts_during_job_execution(self):
        """When stdout is captured (StringIO), toasts are deferred."""
        import sys

        manager = ToastManager()
        notifier = CLINotifier(toast_manager=manager)

        # Capture stdout to simulate job execution context
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            await notifier.send("Test message during job")

            # Toast should NOT be in active list yet (stdout is captured)
            # but it should be deferred
            assert len(manager._toasts) == 0, "Toast should not be active yet"
            assert len(manager._deferred) == 1, "Toast should be deferred"
            assert "Test message during job" in manager._deferred[0].message
        finally:
            sys.stdout = old_stdout

    @pytest.mark.asyncio
    async def test_cli_notifier_shows_deferred_toasts_when_stdout_freed(self):
        """Deferred toasts appear once stdout is no longer captured."""
        import sys

        manager = ToastManager()
        notifier = CLINotifier(toast_manager=manager)

        # Capture stdout to simulate job execution
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            await notifier.send("Deferred message")
            # Toast is deferred, not active
            assert len(manager._toasts) == 0
            assert len(manager._deferred) == 1
        finally:
            sys.stdout = old_stdout

        # Now stdout is free - get_all() should merge deferred toasts
        toasts = manager.get_all()
        assert len(toasts) == 1
        assert "Deferred message" in toasts[0].message
        assert len(manager._deferred) == 0, "Deferred list should be cleared"

    @pytest.mark.asyncio
    async def test_cli_notifier_sends_toasts_immediately_when_not_in_job(self):
        """When stdout is not captured, send toasts immediately."""
        import sys

        # Ensure stdout is not a StringIO
        assert not isinstance(sys.stdout, io.StringIO)

        manager = ToastManager()
        notifier = CLINotifier(toast_manager=manager)

        await notifier.send("Test message")

        # Toast SHOULD be added immediately
        toasts = manager.get_all()
        assert len(toasts) == 1
        assert "Test message" in toasts[0].message


class TestToastHandlerJobContext:
    """Test that ToastHandler detects job execution context."""

    def test_toast_handler_defers_during_job_execution(self):
        """When stdout is captured, defer toasts from logs (don't lose them)."""
        import logging
        import sys

        manager = ToastManager()
        handler = ToastHandler(manager)

        # Capture stdout to simulate job execution context
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # Create a WARNING level log record from src.* module
            record = logging.LogRecord(
                name="src.cron.scheduler",
                level=logging.WARNING,
                pathname="test.py",
                lineno=1,
                msg="Test warning during job",
                args=(),
                exc_info=None,
            )

            handler.emit(record)

            # Toast should be deferred, not lost
            assert len(manager._toasts) == 0, "Toast should not be active yet"
            assert len(manager._deferred) == 1, "Toast should be deferred"
            assert "Test warning during job" in manager._deferred[0].message
        finally:
            sys.stdout = old_stdout

    def test_toast_handler_shows_deferred_when_stdout_freed(self):
        """Deferred log toasts appear once stdout is no longer captured."""
        import logging
        import sys

        manager = ToastManager()
        handler = ToastHandler(manager)

        # Capture stdout to simulate job execution
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            record = logging.LogRecord(
                name="src.cron.scheduler",
                level=logging.WARNING,
                pathname="test.py",
                lineno=1,
                msg="Deferred warning",
                args=(),
                exc_info=None,
            )
            handler.emit(record)
            assert len(manager._deferred) == 1
        finally:
            sys.stdout = old_stdout

        # Now stdout is free - get_all() should merge deferred toasts
        toasts = manager.get_all()
        assert len(toasts) == 1
        assert "Deferred warning" in toasts[0].message
        assert len(manager._deferred) == 0

    def test_toast_handler_creates_toasts_when_not_in_job(self):
        """When stdout is not captured, create toasts from logs immediately."""
        import logging
        import sys

        # Ensure stdout is not a StringIO
        assert not isinstance(sys.stdout, io.StringIO)

        manager = ToastManager()
        handler = ToastHandler(manager)

        # Create a WARNING level log record from src.* module
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

        # Toast SHOULD be added immediately
        toasts = manager.get_all()
        assert len(toasts) == 1
        assert "Test warning" in toasts[0].message

    def test_toast_handler_skips_non_src_modules(self):
        """Don't create toasts from non-src modules even outside job context."""
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

        # Toast should NOT be added (not from src.*)
        toasts = manager.get_all()
        assert len(toasts) == 0
