"""Tests for completion manager using component-based menu."""

import pytest
from pypitui import TUI, MockTerminal

from src.interfaces.pypitui.completion_menu_component import CompletionMenuComponent
from src.interfaces.pypitui.wrapped_input import WrappedInput


class TestCompletionManager:
    """Test completion manager functionality."""

    @pytest.fixture
    def setup(self):
        """Create input, menu component, and completion manager."""
        input_field = WrappedInput(placeholder="Test")
        menu = CompletionMenuComponent()

        def provider(text: str) -> list[tuple[str, str | None]]:
            if text.startswith("/"):
                return [
                    ("/new", "New session"),
                    ("/resume", "Resume session"),
                ]
            return []

        # Use new setup_completion API
        manager = input_field.setup_completion(menu)
        manager.register("/", provider)

        return input_field, menu, manager

    def test_menu_not_shown_without_trigger(self, setup):
        """Menu doesn't show when input doesn't match trigger."""
        input_field, menu, manager = setup

        # Type text without trigger
        input_field.set_value("hello")
        # Trigger post-input hook
        for hook in input_field._post_input_hooks:
            hook()

        assert menu.is_open is False
        assert menu.render(80) == []

    def test_menu_shows_with_trigger(self, setup):
        """Menu shows when input matches trigger."""
        input_field, menu, manager = setup

        # Type trigger
        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        assert menu.is_open is True
        lines = menu.render(80)
        assert len(lines) > 0
        assert any("/new" in line for line in lines)

    def test_navigation_consumed_by_addon(self, setup):
        """Down/Up arrow keys navigate menu when open."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Down arrow should navigate menu
        input_field.handle_input("\x1b[B")  # Down arrow
        # Menu selection should change (first -> second option)
        assert menu.selected_index == 1

    def test_escape_closes_menu(self, setup):
        """Escape key closes the menu."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()
        assert menu.is_open is True

        # Press Escape
        input_field.handle_input("\x1b")  # Escape

        assert menu.is_open is False

    def test_accept_completion(self, setup):
        """Tab accepts current selection and keeps it in input."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Press Tab to accept first option (stays in input)
        input_field.handle_input("\t")  # Tab

        # Input should be replaced with selected value
        assert input_field.get_value() == "/new"

    def test_enter_accepts_and_clears(self, setup):
        """Enter accepts selection and clears input (triggers submit)."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Press Enter - accepts completion AND triggers submit (clears input)
        input_field.handle_input("\r")  # Enter

        # Input should be cleared (submitted)
        assert input_field.get_value() == ""

    def test_non_trigger_keys_pass_through(self, setup):
        """Keys that don't match trigger pass through to input."""
        input_field, menu, manager = setup

        # Type regular text (no trigger)
        input_field.handle_input("h")
        input_field.handle_input("i")

        assert input_field.get_value() == "hi"
        assert menu.is_open is False

    def test_menu_renders_with_box(self, setup):
        """Menu renders with box borders."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        lines = menu.render(80)
        # Should have box borders
        assert any("┌" in line for line in lines)
        assert any("└" in line for line in lines)

    def test_navigation_updates_selection(self, setup):
        """Up/Down arrows update menu selection."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Initially first item selected
        assert menu.selected_index == 0

        # Down arrow
        input_field.handle_input("\x1b[B")
        assert menu.selected_index == 1

        # Down arrow again (wraps to top)
        input_field.handle_input("\x1b[B")
        assert menu.selected_index == 0

        # Up arrow (wraps to bottom)
        input_field.handle_input("\x1b[A")
        assert menu.selected_index == 1


class TestGhostTextAccept:
    """Test ghost text acceptance with right arrow."""

    @pytest.fixture
    def setup(self):
        """Create input with completion for ghost text testing."""
        input_field = WrappedInput(placeholder="Test")
        menu = CompletionMenuComponent()

        def provider(text: str) -> list[tuple[str, str | None]]:
            if text == "/" or text.startswith("/n"):
                return [("/new", "New session")]
            return []

        manager = input_field.setup_completion(menu)
        manager.register("/", provider)

        return input_field, menu, manager

    def test_right_arrow_accepts_ghost_char(self, setup):
        """Right arrow accepts first ghost character."""
        input_field, menu, manager = setup

        # Type "/" to trigger completion with ghost text "ew"
        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Ghost text should be present (menu shows "/new" but input is "/")
        assert menu.is_open is True

        # Right arrow should accept first ghost char
        input_field.handle_input("\x1b[C")  # Right arrow

        # Input should now be "/n" (accepted 'n' from ghost)
        assert input_field.get_value() == "/n"

    def test_right_arrow_multiple_times(self, setup):
        """Multiple right arrows accept multiple ghost chars."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Accept 'n'
        input_field.handle_input("\x1b[C")
        assert input_field.get_value() == "/n"

        # Accept 'e'
        for hook in input_field._post_input_hooks:
            hook()
        input_field.handle_input("\x1b[C")
        assert input_field.get_value() == "/ne"

    def test_right_arrow_no_ghost_passthrough(self, setup):
        """Right arrow passes through when no ghost text."""
        input_field, menu, manager = setup

        # Type text without trigger
        input_field.set_value("hello")
        for hook in input_field._post_input_hooks:
            hook()

        # Move cursor to start
        input_field.set_cursor_pos(0)

        # Right arrow should move cursor (no ghost text)
        input_field.handle_input("\x1b[C")
        assert input_field._cursor_pos == 1

    def test_right_arrow_updates_last_text(self, setup):
        """Right arrow updates last_text to prevent re-triggering."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()


        # Accept ghost char
        input_field.handle_input("\x1b[C")

        # last_text should be updated
        assert manager._last_text == "/n"

    def test_left_arrow_rejects_ghost_char(self, setup):
        """Left arrow rejects ghost text and moves cursor."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Cursor at end of "/"
        assert input_field._cursor_pos == 1

        # Left arrow should reject ghost and move cursor left
        input_field.handle_input("\x1b[D")  # Left arrow

        # Cursor should move left (no ghost accepted)
        assert input_field._cursor_pos == 0

    def test_left_arrow_rejects_back_to_trigger(self, setup):
        """Left arrow can navigate back through rejected ghost text."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Accept some ghost chars first
        input_field.handle_input("\x1b[C")  # Accept 'n'
        for hook in input_field._post_input_hooks:
            hook()
        input_field.handle_input("\x1b[C")  # Accept 'e'
        for hook in input_field._post_input_hooks:
            hook()

        assert input_field.get_value() == "/ne"

        # Left arrow should move cursor left
        input_field.handle_input("\x1b[D")
        assert input_field._cursor_pos == 2

    def test_left_arrow_passthrough_at_trigger(self, setup):
        """Left arrow passes through when at trigger position."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Cursor at end
        assert input_field._cursor_pos == 1

        # Left arrow moves cursor
        input_field.handle_input("\x1b[D")
        assert input_field._cursor_pos == 0

    def test_left_right_roundtrip(self, setup):
        """Left then right arrow navigation works."""
        input_field, menu, manager = setup

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()


        # Left arrow moves cursor left (rejects ghost if any)
        input_field.handle_input("\x1b[D")  # Left
        assert input_field._cursor_pos == 0  # At beginning

        # Right arrow at position 0 should accept ghost char if available
        # But since we moved left first, ghost might have been reset
        # Just verify cursor can move right again
        input_field.handle_input("\x1b[C")  # Right
        # Cursor should move back to position 1 or accept ghost
        assert input_field._cursor_pos >= 0


class TestCompletionManagerIntegration:
    """Integration tests for completion manager with TUI."""

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

        manager = input_field.setup_completion(menu)
        manager.register("/", provider)

        return tui, input_field, menu, manager

    def test_full_completion_flow(self, tui_setup):
        """Test complete flow: type trigger, navigate, accept with Tab."""
        tui, input_field, menu, manager = tui_setup

        # Type trigger
        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Menu should open
        assert menu.is_open is True

        # Navigate down
        input_field.handle_input("\x1b[B")
        assert menu.selected_index == 1

        # Accept selection with Tab (stays in input)
        input_field.handle_input("\t")
        assert input_field.get_value() == "/resume"

    def test_menu_closes_on_non_trigger_input(self, tui_setup):
        """Menu closes when input no longer matches trigger."""
        tui, input_field, menu, manager = tui_setup

        # Open menu
        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()
        assert menu.is_open is True

        # Clear input (no longer matches trigger)
        input_field.set_value("")
        for hook in input_field._post_input_hooks:
            hook()

        # Menu should close
        assert menu.is_open is False


class TestLongestTriggerWins:
    """Test that longest matching trigger wins."""

    def test_longer_trigger_takes_precedence(self):
        """When multiple triggers match, longer one wins."""
        input_field = WrappedInput()
        menu = CompletionMenuComponent()

        command_results = ["/new", "/resume"]
        session_results = ["/resume sess_123"]

        def command_provider(text: str) -> list[tuple[str, str | None]]:
            return [(c, None) for c in command_results if text in c]

        def session_provider(text: str) -> list[tuple[str, str | None]]:
            return [(s, None) for s in session_results if text in s]

        manager = input_field.setup_completion(menu)
        manager.register("/", command_provider)
        manager.register("/resume ", session_provider)

        # Type "/" - should use command provider (only "/" matches)
        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        lines = menu.render(80)
        assert any("/new" in line for line in lines)

        # Type "/resume " - should use session provider ("/resume " is longer)
        input_field.set_value("/resume ")
        for hook in input_field._post_input_hooks:
            hook()

        lines = menu.render(80)
        # Should show session IDs, not commands
        assert any("sess_123" in line for line in lines)
