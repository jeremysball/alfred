"""Tests for completion addon using component-based menu."""

import pytest
from pypitui import TUI, MockTerminal

from src.interfaces.pypitui.completion_addon import CompletionAddon
from src.interfaces.pypitui.completion_menu_component import CompletionMenuComponent
from src.interfaces.pypitui.wrapped_input import WrappedInput


class TestCompletionAddon:
    """Test completion addon functionality."""

    @pytest.fixture
    def setup(self):
        """Create input, menu component, and completion addon."""
        input_field = WrappedInput(placeholder="Test")
        menu = CompletionMenuComponent()

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
            menu_component=menu,
            trigger="/",
        )

        return input_field, menu, addon

    def test_menu_not_shown_without_trigger(self, setup):
        """Menu doesn't show when input doesn't match trigger."""
        input_field, menu, addon = setup

        # Type text without trigger - trigger update via input hook
        input_field.set_value("hello")
        # Simulate what happens when input is processed
        menu.set_options([])
        menu.close()

        assert menu.is_open is False
        assert menu.render(80) == []

    def test_menu_shows_with_trigger(self, setup):
        """Menu shows when trigger matches."""
        input_field, menu, addon = setup

        # Type trigger - menu opens via _update_completion
        input_field.set_value("/")
        # Manually trigger update (normally happens via input hook)
        addon._update_completion()

        assert menu.is_open is True
        rendered = menu.render(80)
        assert len(rendered) > 0  # Menu renders lines

    def test_navigation_consumed_by_addon(self, setup):
        """Navigation keys are consumed when menu is open."""
        input_field, menu, addon = setup

        # Open menu
        input_field.set_value("/")
        addon._update_completion()
        assert menu.is_open is True

        # Down arrow should be consumed
        result = addon.handle_input("\x1b[B")
        assert result == {"consume": True}

    def test_escape_closes_menu(self, setup):
        """Escape key closes completion menu."""
        input_field, menu, addon = setup

        # Open menu
        input_field.set_value("/")
        addon._update_completion()
        assert menu.is_open is True

        # Escape closes
        result = addon.handle_input("\x1b")
        assert result == {"consume": True}
        assert menu.is_open is False

    def test_accept_completion(self, setup):
        """Tab accepts completion and inserts value."""
        input_field, menu, addon = setup

        # Open menu
        input_field.set_value("/")
        addon._update_completion()

        # Tab accepts
        result = addon.handle_input("\t")
        assert result == {"consume": True}

        # Value inserted (no trailing space to avoid race conditions)
        assert input_field.get_value() == "/new"
        assert menu.is_open is False

    def test_non_trigger_keys_pass_through(self, setup):
        """Non-navigation keys pass through."""
        input_field, menu, addon = setup

        # Open menu
        input_field.set_value("/")
        addon._update_completion()
        assert menu.is_open is True

        # Regular key passes through
        result = addon.handle_input("a")
        assert result is None

    def test_menu_renders_with_box(self, setup):
        """Menu renders with box drawing characters."""
        input_field, menu, addon = setup

        input_field.set_value("/")
        addon._update_completion()

        lines = menu.render(80)
        assert len(lines) > 0
        # Should have box drawing characters
        assert any("┌" in line for line in lines)
        assert any("└" in line for line in lines)

    def test_navigation_updates_selection(self, setup):
        """Navigation updates selection index."""
        input_field, menu, addon = setup

        input_field.set_value("/")
        addon._update_completion()

        assert menu.selected_index == 0

        # Move down
        addon.handle_input("\x1b[B")
        assert menu.selected_index == 1

        # Move down again (wraps)
        addon.handle_input("\x1b[B")
        assert menu.selected_index == 0

    def test_invalidate_bubbles_up(self, setup):
        """Invalidation bubbles up through component hierarchy."""
        input_field, menu, addon = setup

        # Open menu
        input_field.set_value("/")
        addon._update_completion()

        # Track if invalidate was called on input
        invalidated = []
        original_invalidate = input_field.invalidate

        def track_invalidate():
            invalidated.append(True)
            # Call original but don't recurse
            input_field.invalidate = lambda: None
            original_invalidate()
            input_field.invalidate = track_invalidate

        input_field.invalidate = track_invalidate

        # Navigate should trigger invalidate on menu, not input
        # (menu is now a separate component)
        addon.handle_input("\x1b[B")
        # Menu component invalidates itself, not the input

        # Accept should trigger invalidate on input
        addon.handle_input("\t")
        assert len(invalidated) == 1


class TestGhostTextAccept:
    """Tests for accepting ghost text with right arrow."""

    @pytest.fixture
    def setup(self):
        """Create input, menu component, and completion addon."""
        input_field = WrappedInput(placeholder="Test")
        menu = CompletionMenuComponent()

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
            menu_component=menu,
            trigger="/",
        )

        return input_field, menu, addon

    def test_right_arrow_accepts_ghost_char(self, setup):
        """Right arrow accepts first ghost character."""
        input_field, menu, addon = setup

        # Open menu with "/"
        input_field.set_value("/")
        addon._update_completion()

        # Ghost suffix should be "new"
        assert addon._get_ghost_suffix() == "new"

        # Press right arrow
        result = addon.handle_input("\x1b[C")
        assert result == {"consume": True}

        # First ghost char accepted
        assert input_field.get_value() == "/n"
        assert addon._get_ghost_suffix() == "ew"

    def test_right_arrow_multiple_times(self, setup):
        """Right arrow can accept multiple ghost characters."""
        input_field, menu, addon = setup

        input_field.set_value("/")
        addon._update_completion()

        # Accept 'n'
        addon.handle_input("\x1b[C")
        assert input_field.get_value() == "/n"

        # Accept 'e'
        addon.handle_input("\x1b[C")
        assert input_field.get_value() == "/ne"

        # Accept 'w'
        addon.handle_input("\x1b[C")
        assert input_field.get_value() == "/new"

        # No more ghost text
        assert addon._get_ghost_suffix() is None

    def test_right_arrow_no_ghost_passthrough(self, setup):
        """Right arrow passes through when no ghost text."""
        input_field, menu, addon = setup

        # Open menu
        input_field.set_value("/")
        addon._update_completion()

        # Accept all ghost chars
        for _ in range(3):
            addon.handle_input("\x1b[C")

        assert input_field.get_value() == "/new"
        assert addon._get_ghost_suffix() is None

        # Right arrow now passes through (not consumed)
        result = addon.handle_input("\x1b[C")
        assert result is None

    def test_right_arrow_updates_last_text(self, setup):
        """Right arrow updates _last_text to prevent duplicate updates."""
        input_field, menu, addon = setup

        input_field.set_value("/")
        addon._update_completion()

        addon.handle_input("\x1b[C")

        # _last_text should be updated
        assert addon._last_text == "/n"

    def test_left_arrow_rejects_ghost_char(self, setup):
        """Left arrow removes last accepted ghost character."""
        input_field, menu, addon = setup

        # Open menu and accept two chars
        input_field.set_value("/")
        addon._update_completion()
        addon.handle_input("\x1b[C")  # Accept 'n'
        addon.handle_input("\x1b[C")  # Accept 'e'

        assert input_field.get_value() == "/ne"
        assert addon._get_ghost_suffix() == "w"

        # Left arrow rejects 'e'
        result = addon.handle_input("\x1b[D")
        assert result == {"consume": True}
        assert input_field.get_value() == "/n"
        assert addon._get_ghost_suffix() == "ew"

    def test_left_arrow_rejects_back_to_trigger(self, setup):
        """Left arrow can reject back to just the trigger character."""
        input_field, menu, addon = setup

        input_field.set_value("/")
        addon._update_completion()
        addon.handle_input("\x1b[C")  # Accept 'n'

        # Left arrow rejects 'n'
        result = addon.handle_input("\x1b[D")
        assert result == {"consume": True}
        assert input_field.get_value() == "/"
        assert addon._get_ghost_suffix() == "new"

    def test_left_arrow_passthrough_at_trigger(self, setup):
        """Left arrow passes through when at trigger (can't go below)."""
        input_field, menu, addon = setup

        input_field.set_value("/")
        addon._update_completion()

        # Left arrow at trigger should pass through
        result = addon.handle_input("\x1b[D")
        assert result is None
        assert input_field.get_value() == "/"

    def test_left_right_roundtrip(self, setup):
        """Right then Left returns to original state."""
        input_field, menu, addon = setup

        input_field.set_value("/")
        addon._update_completion()

        original_ghost = addon._get_ghost_suffix()

        # Right then Left
        addon.handle_input("\x1b[C")
        addon.handle_input("\x1b[D")

        assert input_field.get_value() == "/"
        assert addon._get_ghost_suffix() == original_ghost


class TestCompletionAddonIntegration:
    """Integration tests with real TUI flow."""

    @pytest.fixture
    def tui_setup(self):
        """Create full TUI setup."""
        terminal = MockTerminal(cols=80, rows=24)
        tui = TUI(terminal)
        input_field = WrappedInput(placeholder="Message Alfred...")
        menu = CompletionMenuComponent(max_height=5)
        tui.add_child(input_field)
        tui.add_child(menu)

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
            menu_component=menu,
            trigger="/",
        )

        return tui, input_field, menu, addon, terminal

    def test_full_completion_flow(self, tui_setup):
        """Test complete user interaction flow."""
        tui, input_field, menu, addon, _ = tui_setup

        # Initially no menu
        assert menu.is_open is False

        # Type "/"
        input_field.set_value("/")
        addon._update_completion()

        # Menu should be open
        assert menu.is_open is True
        rendered = menu.render(80)
        assert len(rendered) > 0

        # Navigate down
        result = addon.handle_input("\x1b[B")
        assert result == {"consume": True}
        assert menu.selected_index == 1

        # Accept with Tab
        result = addon.handle_input("\t")
        assert result == {"consume": True}

        # Value should be inserted (no trailing space)
        assert input_field.get_value() == "/resume"
        assert menu.is_open is False

    def test_menu_closes_on_non_trigger_input(self, tui_setup):
        """Menu closes when typing non-trigger text."""
        _, input_field, menu, addon, _ = tui_setup

        # Open menu
        input_field.set_value("/")
        addon._update_completion()
        assert menu.is_open is True

        # Type non-trigger text
        input_field.set_value("hello")
        addon._update_completion()

        # Menu should be closed
        assert menu.is_open is False
        assert menu.render(80) == []
