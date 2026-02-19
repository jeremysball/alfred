"""Tests for the notifier interface and implementations."""

import io
from datetime import datetime, timezone

import pytest

from src.cron.notifier import CLINotifier, Notifier, NotifierError


class TestNotifierABC:
    """Test the Notifier abstract base class."""

    def test_notifier_is_abstract(self):
        """Cannot instantiate Notifier directly."""
        with pytest.raises(TypeError, match="abstract"):
            Notifier()

    def test_notifier_requires_send_method(self):
        """Concrete implementations must implement send()."""

        class IncompleteNotifier(Notifier):
            pass

        with pytest.raises(TypeError, match="abstract"):
            IncompleteNotifier()

    def test_concrete_notifier_can_be_created(self):
        """Complete implementation can be instantiated."""

        class TestNotifier(Notifier):
            async def send(self, message: str) -> None:
                self.last_message = message

        notifier = TestNotifier()
        assert notifier is not None


class TestNotifierError:
    """Test the NotifierError exception."""

    def test_notifier_error_is_exception(self):
        """NotifierError inherits from Exception."""
        error = NotifierError("test message")
        assert isinstance(error, Exception)
        assert str(error) == "test message"

    def test_notifier_error_can_be_raised(self):
        """NotifierError can be raised and caught."""
        with pytest.raises(NotifierError, match="delivery failed"):
            raise NotifierError("delivery failed")


class TestCLINotifier:
    """Test the CLINotifier implementation."""

    async def test_cli_notifier_outputs_to_stream(self):
        """CLINotifier writes formatted message to output stream."""
        output = io.StringIO()
        notifier = CLINotifier(output_stream=output)
        await notifier.send("Test message")
        result = output.getvalue()
        assert "JOB NOTIFICATION" in result
        assert "Test message" in result

    async def test_cli_notifier_includes_timestamp(self):
        """CLINotifier includes timestamp in output."""
        output = io.StringIO()
        notifier = CLINotifier(output_stream=output)
        await notifier.send("Test message")
        result = output.getvalue()
        # Check for timestamp format [YYYY-MM-DD HH:MM:SS
        assert result.startswith("[")
        assert "20" in result  # Year
        assert ":" in result  # Time separator

    async def test_cli_notifier_indents_multiline(self):
        """CLINotifier indents continuation lines."""
        output = io.StringIO()
        notifier = CLINotifier(output_stream=output)
        await notifier.send("Line 1\nLine 2\nLine 3")
        result = output.getvalue()
        lines = result.split("\n")
        # First line has timestamp and label
        assert "Line 1" in lines[0]
        assert lines[0].startswith("[")
        # Continuation lines should be indented (32 spaces)
        assert lines[1].startswith(" " * 32)
        assert "Line 2" in lines[1]
        assert lines[2].startswith(" " * 32)
        assert "Line 3" in lines[2]

    async def test_cli_notifier_handles_empty_message(self):
        """CLINotifier handles empty message gracefully."""
        output = io.StringIO()
        notifier = CLINotifier(output_stream=output)
        await notifier.send("")
        result = output.getvalue()
        # Should just have the label with empty content
        assert "JOB NOTIFICATION" in result

    async def test_cli_notifier_uses_stdout_by_default(self):
        """CLINotifier defaults to sys.stdout."""
        notifier = CLINotifier()
        assert notifier.output is __import__("sys").stdout

    async def test_cli_notifier_graceful_on_write_error(self, caplog):
        """CLINotifier logs error on write failure but doesn't raise."""
        class BrokenStream:
            def write(self, s: str) -> None:
                raise IOError("Stream broken")
            def flush(self) -> None:
                pass

        notifier = CLINotifier(output_stream=BrokenStream())
        # Should not raise
        await notifier.send("Test message")
        # Error should be logged
        assert "Failed to send CLI notification" in caplog.text
