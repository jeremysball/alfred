"""Tests for completion addon using render filter."""

import pytest
from pypitui import MockTerminal, TUI

from src.interfaces.pypitui.completion_addon import CompletionAddon
from src.interfaces.pypitui.wrapped_input import WrappedInput


class TestCompletionAddon:
    """Test completion addon functionality."""

    @pytest.fixture
    def setup(self):
        """Create input and completion addon."""
        input_field = WrappedInput(placeholder="Test")

        def provider(text: str) -> list[tuple[str, str | None]]:
            if text.startswith("/"):
                return [
                    ("/new", "New session"),
                    ("/resume", "Resume session"),
                ]
            return []

        addon = CompletionAddon(
            input_component=input_field,
            provider=provider,
            trigger="/",
        )

        return input_field, addon

    def test_menu_not_shown_without_trigger(self, setup):
        """Menu doesn't show when input doesn't match trigger."""
        input_field, addon = setup

        # Type text without trigger
        input_field.set_value("hello")
        lines = addon._on_render(["input line"], 80)

        assert addon._menu.is_open is False
        assert lines == ["input line"]  # No menu prepended

    def test_menu_shows_with_trigger(self, setup):
        """Menu shows when trigger matches."""
        input_field, addon = setup

        # Type trigger
        input_field.set_value("/")
        lines = addon._on_render(["input line"], 80)

        assert addon._menu.is_open is True
        assert len(lines) > 1  # Menu lines prepended
        assert lines[-1] == "input line"  # Input is last

    def test_navigation_consumed_by_addon(self, setup):
        """Navigation keys are consumed when menu is open."""
        input_field, addon = setup

        # Open menu
        input_field.set_value("/")
        addon._on_render(["input"], 80)

        # Down arrow should be consumed
        result = addon.handle_input("\x1b[B")
        assert result == {"consume": True}

    def test_escape_closes_menu(self, setup):
        """Escape key closes completion menu."""
        input_field, addon = setup

        # Open menu
        input_field.set_value("/")
        addon._on_render(["input"], 80)
        assert addon._menu.is_open is True

        # Escape closes
        result = addon.handle_input("\x1b")
        assert result == {"consume": True}
        assert addon._menu.is_open is False

    def test_accept_completion(self, setup):
        """Tab accepts completion and inserts value."""
        input_field, addon = setup

        # Open menu
        input_field.set_value("/")
        addon._on_render(["input"], 80)

        # Tab accepts
        result = addon.handle_input("\t")
        assert result == {"consume": True}

        # Value inserted with space
        assert input_field.get_value() == "/new "
        assert addon._menu.is_open is False

    def test_non_trigger_keys_pass_through(self, setup):
        """Non-navigation keys pass through."""
        input_field, addon = setup

        # Open menu
        input_field.set_value("/")
        addon._on_render(["input"], 80)

        # Regular key passes through
        result = addon.handle_input("a")
        assert result is None

    def test_menu_prepended_to_lines(self, setup):
        """Menu lines are prepended to input lines."""
        input_field, addon = setup

        input_field.set_value("/")
        input_lines = ["> /"]
        result_lines = addon._on_render(input_lines, 80)

        # Menu should be prepended
        assert len(result_lines) > len(input_lines)
        assert result_lines[-1] == "> /"
        # Should have box drawing characters
        assert any("┌" in line for line in result_lines)
        assert any("└" in line for line in result_lines)

    def test_navigation_updates_selection(self, setup):
        """Navigation updates selection index."""
        input_field, addon = setup

        input_field.set_value("/")
        addon._on_render(["input"], 80)

        assert addon._menu.selected_index == 0

        # Move down
        addon.handle_input("\x1b[B")
        assert addon._menu.selected_index == 1

        # Move down again (wraps)
        addon.handle_input("\x1b[B")
        assert addon._menu.selected_index == 0

    def test_state_change_callback(self, setup):
        """Callback is called when state changes."""
        input_field, _ = setup
        state_changes = []

        def on_state_change():
            state_changes.append(True)

        def provider(text: str) -> list[tuple[str, str | None]]:
            if text.startswith("/"):
                return [("/cmd", "Command")]
            return []

        # Create addon with callback
        addon = CompletionAddon(
            input_component=input_field,
            provider=provider,
            trigger="/",
            on_state_change=on_state_change,
        )

        # Open menu
        input_field.set_value("/")
        addon._on_render(["input"], 80)

        # Navigate should trigger callback
        addon.handle_input("\x1b[B")
        assert len(state_changes) == 1

        # Accept should trigger callback
        addon.handle_input("\t")
        assert len(state_changes) == 2


class TestCompletionAddonIntegration:
    """Integration tests with real TUI flow."""

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
            query = text.lower()
            return [
                (cmd, desc) for cmd, desc in commands
                if query in cmd.lower()
            ]

        addon = CompletionAddon(
            input_component=input_field,
            provider=provider,
            trigger="/",
            max_height=5,
        )

        return tui, input_field, addon, terminal

    def test_full_completion_flow(self, tui_setup):
        """Test complete user interaction flow."""
        tui, input_field, addon, _ = tui_setup

        # Initially no menu
        assert addon._menu.is_open is False

        # Type "/"
        input_field.set_value("/")
        lines = addon._on_render(["> /"], 80)

        # Menu should be open and prepended
        assert addon._menu.is_open is True
        assert len(lines) > 1

        # Navigate down
        result = addon.handle_input("\x1b[B")
        assert result == {"consume": True}
        assert addon._menu.selected_index == 1

        # Accept with Tab
        result = addon.handle_input("\t")
        assert result == {"consume": True}

        # Value should be inserted
        assert input_field.get_value() == "/resume "
        assert addon._menu.is_open is False

    def test_menu_closes_on_non_trigger_input(self, tui_setup):
        """Menu closes when typing non-trigger text."""
        _, input_field, addon, _ = tui_setup

        # Open menu
        input_field.set_value("/")
        addon._on_render(["> /"], 80)
        assert addon._menu.is_open is True

        # Type non-trigger text
        input_field.set_value("hello")
        lines = addon._on_render(["> hello"], 80)

        # Menu should be closed
        assert addon._menu.is_open is False
        assert lines == ["> hello"]  # No menu prepended
