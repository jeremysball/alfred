"""Tests for WrappedInput.with_completion() fluent API."""

from unittest.mock import MagicMock

import pytest

from src.interfaces.pypitui.wrapped_input import WrappedInput


class TestWithCompletionFluentAPI:
    """Test fluent API for adding completion."""

    def test_returns_self_for_chaining(self) -> None:
        """with_completion returns self for method chaining."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[])

        result = input_field.with_completion(provider)

        assert result is input_field

    def test_attaches_completion_addon(self) -> None:
        """with_completion attaches CompletionAddon to input."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/new", "New session")])

        input_field.with_completion(provider, trigger="/")

        # After typing trigger, completion should work
        input_field.handle_input("/")
        lines = input_field.render(width=40)

        # Menu should be in output (above input lines)
        assert any("/new" in line for line in lines)
        assert any("New session" in line for line in lines)

    def test_uses_default_trigger(self) -> None:
        """Default trigger is '/'."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("/help", "Show help")])

        input_field.with_completion(provider)  # No trigger specified

        input_field.handle_input("/")
        lines = input_field.render(width=40)

        assert any("/help" in line for line in lines)

    def test_custom_trigger(self) -> None:
        """Can specify custom trigger character."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[("@user", "User command")])

        input_field.with_completion(provider, trigger="@")

        input_field.handle_input("@")
        lines = input_field.render(width=40)

        assert any("@user" in line for line in lines)

    def test_chaining_with_other_methods(self) -> None:
        """with_completion can be chained with other methods."""
        input_field = (
            WrappedInput(placeholder="Type / for commands")
            .with_completion(lambda t: [("/cmd", "Command")])
        )

        assert input_field.get_value() == ""

        input_field.handle_input("/")
        lines = input_field.render(width=40)

        assert any("/cmd" in line for line in lines)


class TestWithCompletionIntegration:
    """Integration tests for with_completion."""

    def test_provider_called_with_current_text(self) -> None:
        """Provider is called with current input text."""
        input_field = WrappedInput()
        provider = MagicMock(return_value=[])

        input_field.with_completion(provider)

        # Type characters individually (like real terminal input)
        for char in "/ne":
            input_field.handle_input(char)
        input_field.render(width=40)

        provider.assert_called_with("/ne")

    def test_completion_updates_on_typing(self) -> None:
        """Completion menu updates as user types."""
        calls = []

        def provider(text: str) -> list[tuple[str, str | None]]:
            calls.append(text)
            if text.startswith("/n"):
                return [("/new", "New session")]
            elif text.startswith("/r"):
                return [("/resume", "Resume")]
            return [("/new", "New"), ("/resume", "Resume")]

        input_field = WrappedInput().with_completion(provider)

        input_field.handle_input("/")
        input_field.render(width=40)

        input_field.handle_input("n")
        lines = input_field.render(width=40)

        assert "/new" in [line for line in lines if "/new" in line][0]
