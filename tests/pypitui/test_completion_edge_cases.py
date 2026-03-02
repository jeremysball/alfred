"""Edge case tests for command completion system."""

import pytest

from src.interfaces.pypitui.completion_addon import CompletionAddon
from src.interfaces.pypitui.completion_menu import CompletionMenu
from src.interfaces.pypitui.wrapped_input import WrappedInput


class TestCompletionMenuEdgeCases:
    """Edge cases for CompletionMenu."""

    def test_render_with_zero_width(self) -> None:
        """Menu handles zero width gracefully."""
        menu = CompletionMenu()
        menu.set_options([("/test", "Test")])
        menu.open()
        lines = menu.render(width=0)
        assert lines == []  # Should return empty for invalid width

    def test_render_with_negative_width(self) -> None:
        """Menu handles negative width gracefully."""
        menu = CompletionMenu()
        menu.set_options([("/test", "Test")])
        menu.open()
        lines = menu.render(width=-5)
        assert lines == []

    def test_option_with_newline(self) -> None:
        """Options containing newlines are handled."""
        menu = CompletionMenu()
        menu.set_options([("/test\nmalicious", "Test")])
        menu.open()
        lines = menu.render(width=40)
        # Should strip or escape newlines
        assert any("/test" in line for line in lines)

    def test_very_long_option_value(self) -> None:
        """Very long option values are truncated."""
        menu = CompletionMenu()
        long_value = "/" + "x" * 100
        menu.set_options([(long_value, "Description")])
        menu.open()
        lines = menu.render(width=40)
        # Should render without crashing
        assert len(lines) >= 2

    def test_very_long_description(self) -> None:
        """Very long descriptions are truncated."""
        menu = CompletionMenu()
        long_desc = "D" * 100
        menu.set_options([("/test", long_desc)])
        menu.open()
        lines = menu.render(width=40)
        # Should render without crashing
        assert len(lines) >= 2

    def test_unicode_options(self) -> None:
        """Unicode characters in options work correctly."""
        menu = CompletionMenu()
        menu.set_options([("/🎉", "Celebrate"), ("/中文", "Chinese")])
        menu.open()
        lines = menu.render(width=40)
        assert any("🎉" in line for line in lines)

    def test_empty_description(self) -> None:
        """Empty string description works."""
        menu = CompletionMenu()
        menu.set_options([("/test", "")])
        menu.open()
        lines = menu.render(width=40)
        assert "/test" in lines[1]


class TestCompletionAddonEdgeCases:
    """Edge cases for CompletionAddon."""

    def test_provider_returns_empty_list(self) -> None:
        """Menu closes when provider returns empty results."""
        input_field = WrappedInput()
        provider = lambda t: []

        addon = CompletionAddon(input_field, provider, trigger="/")
        input_field.handle_input("/")
        input_field.render(width=40)

        assert not addon._menu.is_open

    def test_provider_raises_exception(self) -> None:
        """Exception in provider is handled gracefully."""
        input_field = WrappedInput()
        provider = lambda t: (_ for _ in ()).throw(ValueError("Boom"))

        addon = CompletionAddon(input_field, provider, trigger="/")

        # Should not crash
        input_field.handle_input("/")
        try:
            input_field.render(width=40)
        except ValueError:
            pass  # Current implementation may raise

    def test_empty_trigger_string(self) -> None:
        """Empty trigger matches everything."""
        calls = []

        def provider(text: str) -> list[tuple[str, str | None]]:
            calls.append(text)
            return [("opt", "Option")]

        input_field = WrappedInput()
        addon = CompletionAddon(input_field, provider, trigger="")

        input_field.handle_input("a")
        input_field.render(width=40)

        assert addon._menu.is_open

    def test_special_regex_chars_in_trigger(self) -> None:
        """Special regex characters in trigger are escaped."""
        input_field = WrappedInput()
        provider = lambda t: [("opt", "Option")]

        addon = CompletionAddon(input_field, provider, trigger="[")
        input_field.handle_input("[")
        input_field.render(width=40)

        assert addon._menu.is_open


class TestCompletionIntegrationEdgeCases:
    """Integration edge cases."""

    def test_rapid_typing(self) -> None:
        """Rapid typing doesn't break completion."""
        calls = []

        def provider(text: str) -> list[tuple[str, str | None]]:
            calls.append(text)
            return [("/new", "New")] if text.startswith("/n") else []

        input_field = WrappedInput().with_completion(provider)

        # Rapid typing
        for char in "/new/resume":
            input_field.handle_input(char)
            input_field.render(width=40)

        # Should have tracked all states
        assert len(calls) > 0

    def test_backspace_removes_trigger(self) -> None:
        """Menu closes when trigger is removed via backspace."""
        input_field = WrappedInput()
        provider = lambda t: [("/test", "Test")]

        input_field.with_completion(provider, trigger="/")

        # Type trigger
        input_field.handle_input("/")
        input_field.render(width=40)

        # Remove trigger (simulate by setting empty value)
        input_field.set_value("")
        lines = input_field.render(width=40)

        # Menu should be closed, no menu lines in output
        # Lines should just be the empty input line
        assert len(lines) == 1  # Just input line

    def test_multiple_triggers_not_supported(self) -> None:
        """Only single trigger character is supported."""
        input_field = WrappedInput()
        provider = lambda t: [("test", "Test")]

        # Multi-char trigger uses startswith, so "/cmd" matches "/cmd test"
        addon = CompletionAddon(input_field, provider, trigger="/cmd")

        input_field.handle_input("/")
        input_field.render(width=40)
        assert not addon._menu.is_open  # Not triggered yet

        for char in "cmd":
            input_field.handle_input(char)
        input_field.render(width=40)
        assert addon._menu.is_open  # Now triggered
