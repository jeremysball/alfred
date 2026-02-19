"""Tests for the notifier interface and implementations."""

import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cron.notifier import CLINotifier, Notifier, NotifierError, TelegramNotifier


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
            async def send(self, message: str, chat_id: int | None = None) -> None:
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

    async def test_cli_notifier_ignores_chat_id(self):
        """CLINotifier accepts chat_id parameter but ignores it."""
        output = io.StringIO()
        notifier = CLINotifier(output_stream=output)
        # Should not raise even with chat_id
        await notifier.send("Test message", chat_id=12345)
        result = output.getvalue()
        assert "Test message" in result


class TestTelegramNotifier:
    """Test the TelegramNotifier implementation."""

    def test_telegram_notifier_stores_bot_and_default_chat_id(self):
        """TelegramNotifier stores bot and default_chat_id."""
        bot = MagicMock()
        notifier = TelegramNotifier(bot=bot, default_chat_id=12345)
        assert notifier.bot is bot
        assert notifier.default_chat_id == 12345

    def test_telegram_notifier_default_chat_id_optional(self):
        """TelegramNotifier can be created without default_chat_id."""
        bot = MagicMock()
        notifier = TelegramNotifier(bot=bot)
        assert notifier.default_chat_id is None

    async def test_telegram_notifier_uses_default_chat_id(self):
        """TelegramNotifier uses default_chat_id when none provided."""
        bot = MagicMock()
        bot.send_message = AsyncMock()
        notifier = TelegramNotifier(bot=bot, default_chat_id=12345)
        await notifier.send("Test message")
        bot.send_message.assert_called_once_with(chat_id=12345, text="Test message")

    async def test_telegram_notifier_uses_explicit_chat_id(self):
        """TelegramNotifier uses explicit chat_id when provided."""
        bot = MagicMock()
        bot.send_message = AsyncMock()
        notifier = TelegramNotifier(bot=bot, default_chat_id=12345)
        await notifier.send("Test message", chat_id=67890)
        bot.send_message.assert_called_once_with(chat_id=67890, text="Test message")

    async def test_telegram_notifier_no_chat_id_logs_warning(self, caplog):
        """TelegramNotifier logs warning when no chat_id available."""
        bot = MagicMock()
        notifier = TelegramNotifier(bot=bot, default_chat_id=None)
        await notifier.send("Test message")
        assert "No chat_id available" in caplog.text
        # Should not call send_message
        bot.send_message.assert_not_called()

    async def test_telegram_notifier_truncates_long_messages(self):
        """TelegramNotifier truncates messages longer than 4096 chars."""
        bot = MagicMock()
        bot.send_message = AsyncMock()
        notifier = TelegramNotifier(bot=bot, default_chat_id=12345)

        # Create a message longer than 4096 chars
        long_message = "x" * 5000
        await notifier.send(long_message)

        # Check that message was truncated
        call_args = bot.send_message.call_args
        sent_text = call_args.kwargs["text"]
        assert len(sent_text) == 4096
        assert sent_text.endswith("...")

    async def test_telegram_notifier_does_not_truncate_short_messages(self):
        """TelegramNotifier does not truncate messages under 4096 chars."""
        bot = MagicMock()
        bot.send_message = AsyncMock()
        notifier = TelegramNotifier(bot=bot, default_chat_id=12345)

        short_message = "x" * 100
        await notifier.send(short_message)

        call_args = bot.send_message.call_args
        sent_text = call_args.kwargs["text"]
        assert sent_text == short_message

    async def test_telegram_notifier_graceful_on_api_error(self, caplog):
        """TelegramNotifier logs error on API failure but doesn't raise."""
        bot = MagicMock()
        bot.send_message = AsyncMock(side_effect=Exception("API error"))
        notifier = TelegramNotifier(bot=bot, default_chat_id=12345)

        # Should not raise
        await notifier.send("Test message")

        # Error should be logged
        assert "Failed to send Telegram notification" in caplog.text
