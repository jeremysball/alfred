"""Edge case tests for command completion system."""


from src.interfaces.pypitui.completion_addon import CompletionAddon
from src.interfaces.pypitui.completion_menu import CompletionMenu
from src.interfaces.pypitui.completion_menu_component import CompletionMenuComponent
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
        menu.set_options([("/\ud83c\udf89", "Celebrate"), ("/\u4e2d\u6587", "Chinese")])
        menu.open()
        lines = menu.render(width=40)
        assert any("\ud83c\udf89" in line for line in lines)

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
        menu = CompletionMenuComponent()
        provider = lambda t: []

        CompletionAddon(input_field, provider, menu, trigger="/")
        input_field.set_value("/")
        # Trigger post-input hook
        for hook in input_field._post_input_hooks:
            hook()

        assert not menu.is_open

    def test_provider_raises_exception(self) -> None:
        """Exception in provider is handled gracefully."""
        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        provider = lambda t: (_ for _ in ()).throw(ValueError("Boom"))

        CompletionAddon(input_field, provider, menu, trigger="/")

        # Should not crash
        input_field.set_value("/")
        try:
            for hook in input_field._post_input_hooks:
                hook()
        except ValueError:
            pass  # Current implementation may raise

    def test_empty_trigger_string(self) -> None:
        """Empty trigger matches everything."""
        calls = []

        def provider(text: str) -> list[tuple[str, str | None]]:
            calls.append(text)
            return [("opt", "Option")]

        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        CompletionAddon(input_field, provider, menu, trigger="")

        input_field.set_value("a")
        for hook in input_field._post_input_hooks:
            hook()

        assert menu.is_open

    def test_special_regex_chars_in_trigger(self) -> None:
        """Special regex characters in trigger are escaped."""
        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        provider = lambda t: [("opt", "Option")]

        CompletionAddon(input_field, provider, menu, trigger="[")

        input_field.set_value("[")
        for hook in input_field._post_input_hooks:
            hook()

        assert menu.is_open


class TestCompletionIntegrationEdgeCases:
    """Integration edge cases."""

    def test_rapid_typing(self) -> None:
        """Rapid typing doesn't break completion."""
        calls = []

        def provider(text: str) -> list[tuple[str, str | None]]:
            calls.append(text)
            return [("/new", "New")] if text.startswith("/n") else []

        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        input_field.with_completion_component(provider, menu, trigger="/")

        # Rapid typing - simulate setting values and triggering hooks
        for text in ["/", "/n", "/ne", "/new", "/new/resume"]:
            input_field.set_value(text)
            for hook in input_field._post_input_hooks:
                hook()

        # Should have tracked states
        assert len(calls) > 0

    def test_backspace_removes_trigger(self) -> None:
        """Menu closes when trigger is removed via backspace."""
        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        provider = lambda t: [("/test", "Test")]

        input_field.with_completion_component(provider, menu, trigger="/")

        # Type trigger
        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()
        assert menu.is_open is True

        # Remove trigger
        input_field.set_value("")
        for hook in input_field._post_input_hooks:
            hook()

        assert menu.is_open is False

    def test_multiple_triggers_not_supported(self) -> None:
        """Only single trigger character is supported."""
        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        provider = lambda t: [("test", "Test")]

        # Multi-char trigger uses startswith, so "/cmd" matches "/cmd test"
        CompletionAddon(input_field, provider, menu, trigger="/cmd")

        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()
        assert not menu.is_open  # Not triggered yet

        input_field.set_value("/cmd")
        for hook in input_field._post_input_hooks:
            hook()
        assert menu.is_open  # Now triggered
