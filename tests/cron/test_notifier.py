"""Tests for the notifier interface and implementations."""

import pytest

from src.cron.notifier import Notifier, NotifierError


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
