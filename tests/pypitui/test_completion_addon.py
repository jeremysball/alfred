"""Tests for CompletionAddon component."""

from unittest.mock import MagicMock

import pytest

from pypitui import Key, matches_key

from src.interfaces.pypitui.completion_addon import CompletionAddon
from src.interfaces.pypitui.wrapped_input import WrappedInput

# Terminal escape sequences for key inputs
KEY_UP = "\x1b[A"
KEY_DOWN = "\x1b[B"
KEY_RIGHT = "\x1b[C"
KEY_LEFT = "\x1b[D"
KEY_TAB = "\t"
KEY_ENTER = "\r"
KEY_ESCAPE = "\x1b"
KEY_BACKSPACE = "backspace"


class TestCompletionAddonInit:
    """Test CompletionAddon initialization."""

    def test_addon_attaches_to_input(self) -> None:
        """CompletionAddon attaches to WrappedInput via hooks."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[])

        addon = CompletionAddon(input_field, provider, trigger="/")

        assert addon._input is input_field
        assert addon._provider is provider
        assert addon._trigger == "/"

    def test_addon_registers_filters(self) -> None:
        """Addon registers input and render filters."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[])

        CompletionAddon(input_field, provider, trigger="/")

        # Should have registered filters
        assert len(input_field._input_filters) > 0
        assert len(input_field._render_filters) > 0


class TestCompletionAddonProvider:
    """Test provider invocation."""

    def test_provider_called_when_trigger_matches(self) -> None:
        """Provider called when text starts with trigger."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/new", "New session")])

        CompletionAddon(input_field, provider, trigger="/")

        # Type "/"
        input_field.handle_input("/")
        # Trigger render to update completion state
        input_field.render(width=40)

        # Provider should have been called
        provider.assert_called_with("/")

    def test_provider_not_called_when_no_trigger(self) -> None:
        """Provider not called when text doesn't start with trigger."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[])

        CompletionAddon(input_field, provider, trigger="/")

        # Type regular text
        input_field.handle_input("h")
        input_field.handle_input("i")

        # Provider should not have been called
        provider.assert_not_called()

    def test_provider_called_with_full_text(self) -> None:
        """Provider receives full input text."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[])

        CompletionAddon(input_field, provider, trigger="/")

        # Type "/resume abc"
        for char in "/resume abc":
            input_field.handle_input(char)
            input_field.render(width=40)

        # Provider should have been called with full text
        calls = provider.call_args_list
        assert calls[-1][0][0] == "/resume abc"


class TestCompletionAddonMenu:
    """Test menu display."""

    def test_menu_opens_when_provider_returns_options(self) -> None:
        """Menu opens when provider returns completion options."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/new", "New session")])

        addon = CompletionAddon(input_field, provider, trigger="/")

        # Type "/"
        input_field.handle_input("/")
        input_field.render(width=40)

        assert addon._menu.is_open

    def test_menu_closes_when_no_options(self) -> None:
        """Menu closes when provider returns empty list."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[])

        addon = CompletionAddon(input_field, provider, trigger="/")

        # Type "/" then backspace (simulated by provider returning empty)
        provider.return_value = [("/new", "New")]
        input_field.handle_input("/")
        input_field.render(width=40)
        assert addon._menu.is_open

        # Now provider returns empty
        provider.return_value = []
        input_field.handle_input("x")  # Trigger update
        input_field.render(width=40)

        assert not addon._menu.is_open

    def test_menu_closes_when_trigger_deleted(self) -> None:
        """Menu closes when trigger prefix is deleted."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/new", "New session")])

        addon = CompletionAddon(input_field, provider, trigger="/")

        # Type "/" then delete it
        input_field.handle_input("/")
        input_field.render(width=40)
        assert addon._menu.is_open

        # Delete the "/" by setting empty value (backspace not available in tests)
        input_field.set_value("")
        input_field.render(width=40)

        assert not addon._menu.is_open


class TestCompletionAddonNavigation:
    """Test menu navigation."""

    def test_down_arrow_moves_selection(self) -> None:
        """Down arrow moves menu selection down."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[
            ("/new", "New session"),
            ("/resume", "Resume"),
        ])

        addon = CompletionAddon(input_field, provider, trigger="/")
        input_field.handle_input("/")
        input_field.render(width=40)

        assert addon._menu.selected_index == 0

        # Simulate down arrow
        input_field.handle_input(KEY_DOWN)

        assert addon._menu.selected_index == 1

    def test_up_arrow_moves_selection(self) -> None:
        """Up arrow moves menu selection up."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[
            ("/new", "New session"),
            ("/resume", "Resume"),
        ])

        addon = CompletionAddon(input_field, provider, trigger="/")
        input_field.handle_input("/")
        input_field.render(width=40)
        input_field.handle_input(KEY_DOWN)  # Move to index 1

        # Simulate up arrow
        input_field.handle_input(KEY_UP)

        assert addon._menu.selected_index == 0

    def test_navigation_does_not_affect_input(self) -> None:
        """Arrow keys navigate menu without moving text cursor."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[
            ("/new", "New session"),
            ("/resume", "Resume"),
        ])

        CompletionAddon(input_field, provider, trigger="/")

        # Type "/abc"
        for char in "/abc":
            input_field.handle_input(char)
        input_field.render(width=40)

        cursor_pos_before = input_field._cursor_pos

        # Simulate down arrow
        input_field.handle_input(KEY_DOWN)

        # Cursor should not have moved
        assert input_field._cursor_pos == cursor_pos_before


class TestCompletionAddonAccept:
    """Test completion acceptance."""

    def test_tab_accepts_completion(self) -> None:
        """Tab accepts the selected completion."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/new", "New session")])

        CompletionAddon(input_field, provider, trigger="/")

        # Type "/"
        input_field.handle_input("/")
        input_field.render(width=40)

        # Press Tab
        input_field.handle_input(KEY_TAB)

        # Value should be updated
        assert "/new" in input_field.get_value()

    def test_enter_accepts_completion(self) -> None:
        """Enter accepts the selected completion."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/new", "New session")])

        CompletionAddon(input_field, provider, trigger="/")

        # Type "/"
        input_field.handle_input("/")
        input_field.render(width=40)

        # Press Enter
        input_field.handle_input(KEY_ENTER)

        # Value should be updated
        assert "/new" in input_field.get_value()

    def test_accept_closes_menu(self) -> None:
        """Accepting completion closes the menu."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/new", "New session")])

        addon = CompletionAddon(input_field, provider, trigger="/")

        # Type "/" and accept
        input_field.handle_input("/")
        input_field.render(width=40)
        assert addon._menu.is_open

        input_field.handle_input(KEY_TAB)

        assert not addon._menu.is_open

    def test_accept_adds_space_after(self) -> None:
        """Accepting completion adds trailing space for arguments."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/resume", "Resume session")])

        CompletionAddon(input_field, provider, trigger="/")

        # Type "/re" and accept
        input_field.handle_input("/")
        input_field.handle_input("r")
        input_field.handle_input("e")
        input_field.render(width=40)

        input_field.handle_input(KEY_TAB)

        # Should have trailing space
        assert input_field.get_value() == "/resume "


class TestCompletionAddonCancel:
    """Test menu cancellation."""

    def test_esc_closes_menu(self) -> None:
        """Escape closes menu without accepting."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/new", "New session")])

        addon = CompletionAddon(input_field, provider, trigger="/")

        # Type "/"
        input_field.handle_input("/")
        input_field.render(width=40)
        assert addon._menu.is_open

        # Press Escape
        input_field.handle_input(KEY_ESCAPE)

        assert not addon._menu.is_open

    def test_esc_preserves_text(self) -> None:
        """Escape closes menu but keeps current text."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/new", "New session")])

        CompletionAddon(input_field, provider, trigger="/")

        # Type "/abc"
        for char in "/abc":
            input_field.handle_input(char)
        input_field.render(width=40)

        # Press Escape
        input_field.handle_input(KEY_ESCAPE)

        # Text should be preserved
        assert input_field.get_value() == "/abc"


class TestCompletionAddonRender:
    """Test menu rendering integration."""

    def test_menu_renders_above_input(self) -> None:
        """Menu appears above input in rendered output."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/new", "New")])

        CompletionAddon(input_field, provider, trigger="/")

        # Type "/"
        input_field.handle_input("/")

        # Render
        lines = input_field.render(width=40)

        # Menu should be in output (above input)
        # Menu has box borders, input is just text
        box_lines = [line for line in lines if "┌" in line or "└" in line]
        assert len(box_lines) > 0


class TestCompletionAddonCustomTrigger:
    """Test custom trigger prefixes."""

    def test_custom_trigger(self) -> None:
        """Addon works with custom trigger character."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("@user", "User command")])

        CompletionAddon(input_field, provider, trigger="@")

        # Type "@"
        input_field.handle_input("@")
        input_field.render(width=40)

        provider.assert_called_with("@")
        assert input_field._render_filters  # Menu should be active


class TestCompletionAddonMaxHeight:
    """Test max_height parameter."""

    def test_max_height_limits_menu(self) -> None:
        """max_height limits the number of visible options."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[
            ("/a", "A"),
            ("/b", "B"),
            ("/c", "C"),
            ("/d", "D"),
        ])

        addon = CompletionAddon(input_field, provider, trigger="/", max_height=2)

        # Type "/"
        input_field.handle_input("/")
        input_field.render(width=40)

        assert addon._menu._max_height == 2
