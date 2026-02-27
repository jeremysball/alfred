"""Tests for toast notification system (Phase 4.5)."""

import logging
from datetime import datetime, timedelta

import pytest


@pytest.fixture(autouse=True)
def clean_toasts():
    """Ensure toasts are clean before and after each test."""
    from src.interfaces.pypitui.toast import dismiss_all

    dismiss_all()
    yield
    dismiss_all()


class TestToastMessage:
    """Tests for ToastMessage dataclass (Phase 4.5.1)."""

    def test_toast_message_defaults(self):
        """Verify created timestamp auto-populates."""
        from src.interfaces.pypitui.toast import ToastMessage

        toast = ToastMessage(message="Test warning", level="warning")

        assert toast.message == "Test warning"
        assert toast.level == "warning"
        assert isinstance(toast.created, datetime)

    def test_toast_message_levels(self):
        """Verify warning/error/info levels work."""
        from src.interfaces.pypitui.toast import ToastMessage

        warning = ToastMessage(message="Warn", level="warning")
        error = ToastMessage(message="Err", level="error")
        info = ToastMessage(message="Info", level="info")

        assert warning.level == "warning"
        assert error.level == "error"
        assert info.level == "info"


class TestToastHandler:
    """Tests for ToastHandler logging handler (Phase 4.5.2)."""

    def test_toast_handler_captures_warning(self):
        """Verify WARNING logs create toast."""
        from src.interfaces.pypitui.toast import ToastHandler, dismiss_all, get_toasts

        dismiss_all()
        handler = ToastHandler()
        logger = logging.getLogger("src.test_module_unique_1")
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

        logger.warning("Test warning message unique")

        toasts = get_toasts()
        # Find our specific toast
        our_toasts = [t for t in toasts if "unique" in t.message]
        assert len(our_toasts) == 1
        assert our_toasts[0].level == "warning"

        logger.removeHandler(handler)
        dismiss_all()

    def test_toast_handler_captures_error(self):
        """Verify ERROR logs create toast."""
        from src.interfaces.pypitui.toast import ToastHandler, dismiss_all, get_toasts

        dismiss_all()
        handler = ToastHandler()
        logger = logging.getLogger("src.test_error_unique_2")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)

        logger.error("Test error message unique")

        toasts = get_toasts()
        our_toasts = [t for t in toasts if "unique" in t.message]
        assert len(our_toasts) == 1
        assert our_toasts[0].level == "error"

        logger.removeHandler(handler)
        dismiss_all()

    def test_toast_handler_ignores_info(self):
        """Verify INFO logs don't create toast."""
        from src.interfaces.pypitui.toast import ToastHandler, get_toasts

        handler = ToastHandler()
        logger = logging.getLogger("src.test_info_unique_3")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        logger.info("Test info message")

        toasts = get_toasts()
        assert len(toasts) == 0

        logger.removeHandler(handler)

    def test_toast_handler_filters_non_src(self):
        """Verify only src.* modules captured."""
        from src.interfaces.pypitui.toast import ToastHandler, get_toasts

        handler = ToastHandler()
        logger = logging.getLogger("other.module.unique")
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

        logger.warning("External warning")

        toasts = get_toasts()
        assert len(toasts) == 0

        logger.removeHandler(handler)


class TestToastManager:
    """Tests for toast management (Phase 4.5.3)."""

    def test_max_visible_toasts(self):
        """Verify only MAX_VISIBLE_TOASTS kept."""
        from src.interfaces.pypitui.toast import (
            MAX_VISIBLE_TOASTS,
            ToastHandler,
            get_toasts,
        )

        handler = ToastHandler()
        logger = logging.getLogger("src.test_max_unique")
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

        # Add more than max
        for i in range(MAX_VISIBLE_TOASTS + 2):
            logger.warning(f"Warning {i}")

        toasts = get_toasts()
        assert len(toasts) == MAX_VISIBLE_TOASTS
        # Should keep most recent
        assert "Warning 4" in toasts[-1].message

        logger.removeHandler(handler)

    def test_dismiss_expired_toasts(self):
        """Verify expired toasts are removed."""
        from src.interfaces.pypitui.toast import (
            TOAST_DURATION_SECONDS,
            ToastMessage,
            dismiss_expired,
            get_toasts,
        )

        # Add an old toast
        old_toast = ToastMessage(message="Old", level="warning")
        old_toast.created = datetime.now() - timedelta(seconds=TOAST_DURATION_SECONDS + 1)
        get_toasts().append(old_toast)

        # Add a fresh toast
        fresh_toast = ToastMessage(message="Fresh", level="warning")
        get_toasts().append(fresh_toast)

        dismiss_expired()

        toasts = get_toasts()
        assert len(toasts) == 1
        assert toasts[0].message == "Fresh"

    def test_dismiss_all_toasts(self):
        """Verify dismiss_all clears all toasts."""
        from src.interfaces.pypitui.toast import ToastHandler, dismiss_all, get_toasts

        dismiss_all()
        handler = ToastHandler()
        logger = logging.getLogger("src.test_dismiss_unique_final")
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

        logger.warning("Warning dismiss unique")
        logger.warning("Warning dismiss unique 2")

        # Check our toasts exist
        before = [t for t in get_toasts() if "dismiss unique" in t.message]
        assert len(before) == 2

        dismiss_all()

        assert len(get_toasts()) == 0

        logger.removeHandler(handler)
