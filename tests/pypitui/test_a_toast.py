"""Tests for toast notification system (Phase 4.5)."""

import logging
from datetime import datetime, timedelta

import pytest


class TestToastMessage:
    """Tests for ToastMessage dataclass."""

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


class TestToastManager:
    """Tests for ToastManager class."""

    def test_add_and_get_toasts(self):
        """Verify toasts can be added and retrieved."""
        from src.interfaces.pypitui.toast import ToastManager

        manager = ToastManager()
        manager.add("Warning message", "warning")
        manager.add("Error message", "error")

        toasts = manager.get_all()
        assert len(toasts) == 2
        assert toasts[0].message == "Warning message"
        assert toasts[0].level == "warning"
        assert toasts[1].message == "Error message"
        assert toasts[1].level == "error"

    def test_max_visible_toasts(self):
        """Verify only MAX_VISIBLE_TOASTS kept."""
        from src.interfaces.pypitui.toast import MAX_VISIBLE_TOASTS, ToastManager

        manager = ToastManager()

        # Add more than max
        for i in range(MAX_VISIBLE_TOASTS + 2):
            manager.add(f"Warning {i}", "warning")

        toasts = manager.get_all()
        assert len(toasts) == MAX_VISIBLE_TOASTS
        # Should keep most recent
        assert "Warning 4" in toasts[-1].message

    def test_dismiss_expired_toasts(self):
        """Verify expired toasts are removed."""
        from src.interfaces.pypitui.toast import (
            TOAST_DURATION_SECONDS,
            ToastManager,
            ToastMessage,
        )

        manager = ToastManager()

        # Add an old toast directly to internal list
        old_toast = ToastMessage(message="Old", level="warning")
        old_toast.created = datetime.now() - timedelta(seconds=TOAST_DURATION_SECONDS + 1)
        manager._toasts.append(old_toast)

        # Add a fresh toast
        manager.add("Fresh", "warning")

        manager.dismiss_expired()

        toasts = manager.get_all()
        assert len(toasts) == 1
        assert toasts[0].message == "Fresh"

    def test_dismiss_all_toasts(self):
        """Verify dismiss_all clears all toasts."""
        from src.interfaces.pypitui.toast import ToastManager

        manager = ToastManager()
        manager.add("Warning 1", "warning")
        manager.add("Warning 2", "warning")

        assert len(manager.get_all()) == 2

        manager.dismiss_all()

        assert len(manager.get_all()) == 0


class TestToastHandler:
    """Tests for ToastHandler logging handler."""

    def test_toast_handler_captures_warning(self):
        """Verify WARNING logs create toast."""
        from src.interfaces.pypitui.toast import ToastHandler, ToastManager

        manager = ToastManager()
        handler = ToastHandler(manager)
        logger = logging.getLogger("src.test_module_unique_1")
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

        logger.warning("Test warning message unique")

        toasts = manager.get_all()
        assert len(toasts) == 1
        assert "unique" in toasts[0].message
        assert toasts[0].level == "warning"

        logger.removeHandler(handler)

    def test_toast_handler_captures_error(self):
        """Verify ERROR logs create toast."""
        from src.interfaces.pypitui.toast import ToastHandler, ToastManager

        manager = ToastManager()
        handler = ToastHandler(manager)
        logger = logging.getLogger("src.test_error_unique_2")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)

        logger.error("Test error message unique")

        toasts = manager.get_all()
        assert len(toasts) == 1
        assert "unique" in toasts[0].message
        assert toasts[0].level == "error"

        logger.removeHandler(handler)

    def test_toast_handler_ignores_info(self):
        """Verify INFO logs don't create toast."""
        from src.interfaces.pypitui.toast import ToastHandler, ToastManager

        manager = ToastManager()
        handler = ToastHandler(manager)
        logger = logging.getLogger("src.test_info_unique_3")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        logger.info("Test info message")

        toasts = manager.get_all()
        assert len(toasts) == 0

        logger.removeHandler(handler)

    def test_toast_handler_filters_non_src(self):
        """Verify only src.* modules captured."""
        from src.interfaces.pypitui.toast import ToastHandler, ToastManager

        manager = ToastManager()
        handler = ToastHandler(manager)
        logger = logging.getLogger("other.module.unique")
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

        logger.warning("External warning")

        toasts = manager.get_all()
        assert len(toasts) == 0

        logger.removeHandler(handler)
