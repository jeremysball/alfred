"""Tests for completion overlay v2 using pypitui 0.3.0 overlay system."""

import pytest
from pypitui import TUI, MockTerminal

from src.interfaces.pypitui.completion_overlay_v2 import CompletionOverlayV2
from src.interfaces.pypitui.wrapped_input import WrappedInput


class TestCompletionOverlayV2:
    """Test completion overlay v2 functionality."""

    @pytest.fixture
    def setup(self):
        """Create TUI with input and completion overlay."""
        terminal = MockTerminal(cols=80, rows=24)
        tui = TUI(terminal)
        input_field = WrappedInput(placeholder="Test")
        tui.add_child(input_field)

        def provider(text: str) -> list[tuple[str, str | None]]:
            if text.startswith("/"):
                return [
                    ("/new", "New session"),
                    ("/resume", "Resume session"),
                ]
            return []

        overlay = CompletionOverlayV2(
            tui=tui,
            input_component=input_field,
            provider=provider,
            trigger="/",
        )

        return tui, input_field, overlay, terminal

    def test_overlay_not_shown_without_trigger(self, setup):
        """Menu doesn't show when input doesn't match trigger."""
        tui, input_field, overlay, _ = setup

        # Type text without trigger
        input_field.set_value("hello")
        overlay._update_completion()

        assert overlay._menu.is_open is False
        assert overlay._overlay_handle is None

    def test_overlay_shows_with_trigger(self, setup):
        """Menu shows when trigger matches."""
        tui, input_field, overlay, _ = setup

        # Type trigger
        input_field.set_value("/")
        overlay._update_completion()

        assert overlay._menu.is_open is True
        # Overlay handle created
        assert overlay._overlay_handle is not None

    def test_navigation_consumed_by_overlay(self, setup):
        """Navigation keys are consumed when menu is open."""
        tui, input_field, overlay, _ = setup

        # Open menu
        input_field.set_value("/")
        overlay._update_completion()

        # Down arrow should be consumed (return True)
        result = overlay._on_input("\x1b[B")
        assert result is True

    def test_escape_closes_menu(self, setup):
        """Escape key closes completion menu."""
        tui, input_field, overlay, _ = setup

        # Open menu
        input_field.set_value("/")
        overlay._update_completion()

        # Escape closes (returns True)
        result = overlay._on_input("\x1b")
        assert result is True
        assert overlay._menu.is_open is False

    def test_accept_completion(self, setup):
        """Tab accepts completion and inserts value."""
        tui, input_field, overlay, _ = setup

        # Open menu
        input_field.set_value("/")
        overlay._update_completion()

        # Tab accepts (returns True)
        result = overlay._on_input("\t")
        assert result is True

        # Value inserted with space
        assert input_field.get_value() == "/new "
        assert overlay._menu.is_open is False

    def test_non_trigger_keys_pass_through(self, setup):
        """Non-navigation keys pass through to input."""
        tui, input_field, overlay, _ = setup

        # Open menu
        input_field.set_value("/")
        overlay._update_completion()

        # Regular key passes through (returns False)
        result = overlay._on_input("a")
        assert result is False

    def test_cleanup_closes_overlay(self, setup):
        """Cleanup closes overlay."""
        tui, input_field, overlay, _ = setup

        # Open menu
        input_field.set_value("/")
        overlay._update_completion()

        # Cleanup
        overlay._close_overlay()

        assert overlay._menu.is_open is False
        assert overlay._overlay_handle is None


class TestCompletionOverlayV2Integration:
    """Integration tests with real TUI input flow."""

    @pytest.fixture
    def tui_setup(self):
        """Create full TUI setup."""
        terminal = MockTerminal(cols=80, rows=24)
        tui = TUI(terminal)
        input_field = WrappedInput(placeholder="Message Alfred...")
        tui.add_child(input_field)

        def provider(text: str) -> list[tuple[str, str | None]]:
            commands = [
                ("/new", "Start new session"),
                ("/resume", "Resume previous"),
                ("/sessions", "List sessions"),
            ]
            if not text.startswith("/"):
                return []
            # Fuzzy filter
            query = text.lower()
            return [
                (cmd, desc) for cmd, desc in commands
                if query in cmd.lower()
            ]

        overlay = CompletionOverlayV2(
            tui=tui,
            input_component=input_field,
            provider=provider,
            trigger="/",
            max_height=5,
        )

        return tui, input_field, overlay, terminal

    def test_completion_updates_via_render_filter(self, tui_setup):
        """Test that completion updates when render filter is called."""
        tui, input_field, overlay, _ = tui_setup

        # Initially menu is closed
        assert overlay._menu.is_open is False

        # Set input value
        input_field.set_value("/")

        # Trigger render filter to update completion
        overlay._on_render([], 80)

        # Menu should now be open
        assert overlay._menu.is_open is True
        assert overlay._overlay_handle is not None

    def test_navigation_and_acceptance(self, tui_setup):
        """Test navigation and completion acceptance."""
        tui, input_field, overlay, _ = tui_setup

        # Set up completion menu
        input_field.set_value("/")
        overlay._update_completion()

        assert overlay._menu.is_open
        assert overlay._menu.selected_index == 0

        # Navigate down
        consumed = overlay._on_input("\x1b[B")
        assert consumed is True
        assert overlay._menu.selected_index == 1

        # Accept with Tab
        consumed = overlay._on_input("\t")
        assert consumed is True

        # Value should be inserted
        assert input_field.get_value() == "/resume "
        assert overlay._menu.is_open is False
