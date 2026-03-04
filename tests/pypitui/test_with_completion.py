"""Tests for WrappedInput.with_completion_component() and setup_completion() APIs."""

from unittest.mock import MagicMock

from pypitui import TUI, MockTerminal

from src.interfaces.pypitui.completion_menu_component import CompletionMenuComponent
from src.interfaces.pypitui.wrapped_input import WrappedInput


class TestWithCompletionFluentAPI:
    """Test fluent API for adding completion."""

    def test_returns_self_for_chaining(self) -> None:
        """with_completion_component returns self for method chaining."""
        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        provider = MagicMock(return_value=[])

        result = input_field.with_completion_component(provider, menu)

        assert result is input_field

    def test_attaches_completion_addon(self) -> None:
        """with_completion attaches CompletionAddon to input."""

        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        provider = MagicMock(return_value=[("/new", "New session")])

        input_field.with_completion_component(provider, menu, trigger="/")

        # CompletionAddon should be registered
        assert len(input_field._post_input_hooks) > 0

    def test_uses_default_trigger(self) -> None:
        """Default trigger is '/'."""
        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        provider = MagicMock(return_value=[("/help", "Show help")])

        input_field.with_completion_component(provider, menu)  # No trigger specified

        input_field.set_value("/")
        # Trigger post-input hook manually (normally called after handle_input)
        for hook in input_field._post_input_hooks:
            hook()

        assert menu.is_open is True

    def test_custom_trigger(self) -> None:
        """Can specify custom trigger character."""
        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        provider = MagicMock(return_value=[("@user", "User command")])

        input_field.with_completion_component(provider, menu, trigger="@")

        input_field.set_value("@")
        for hook in input_field._post_input_hooks:
            hook()

        assert menu.is_open is True

    def test_chaining_with_other_methods(self) -> None:
        """with_completion_component can be chained with other methods."""
        menu = CompletionMenuComponent()
        input_field = (
            WrappedInput(placeholder="Type / for commands")
            .with_completion_component(lambda t: [("/cmd", "Command")], menu)
        )

        assert input_field.get_value() == ""


class TestWithCompletionIntegration:
    """Integration tests for with_completion_component."""

    def test_provider_called_with_current_text(self) -> None:
        """Provider is called with current input text."""
        input_field = WrappedInput()
        menu = CompletionMenuComponent()
        provider = MagicMock(return_value=[])

        input_field.with_completion_component(provider, menu)

        # Set value and trigger post-input hook
        input_field.set_value("/ne")
        for hook in input_field._post_input_hooks:
            hook()

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

        menu = CompletionMenuComponent()
        input_field = WrappedInput().with_completion_component(provider, menu)

        # Simulate typing "/"
        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()
        assert menu.is_open is True

        # Simulate typing "n"
        input_field.set_value("/n")
        for hook in input_field._post_input_hooks:
            hook()

        # Menu should still be open with filtered results
        assert menu.is_open is True
        rendered = menu.render(40)
        assert any("/new" in line for line in rendered)


class TestWithCompletionComponentInTUI:
    """Integration tests with real TUI layout."""

    def test_menu_renders_in_layout(self) -> None:
        """Completion menu renders as separate component in TUI layout."""
        terminal = MockTerminal(cols=80, rows=24)
        tui = TUI(terminal)

        input_field = WrappedInput(placeholder="Test")
        menu = CompletionMenuComponent()

        def provider(text: str) -> list[tuple[str, str | None]]:
            if text.startswith("/"):
                return [("/test", "Test command")]
            return []

        input_field.with_completion_component(provider, menu, trigger="/")

        # Add to layout: menu between status and input
        tui.add_child(menu)
        tui.add_child(input_field)

        # Initially menu is closed (empty)
        lines = tui.render(80)
        assert not any("┌" in line for line in lines)  # No box border

        # Type trigger
        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        # Menu should now render
        lines = tui.render(80)
        assert any("┌" in line for line in lines)  # Box border present
        assert any("/test" in line for line in lines)

    def test_menu_closes_when_input_cleared(self) -> None:
        """Menu component closes and clears from layout when input cleared."""
        terminal = MockTerminal(cols=80, rows=24)
        tui = TUI(terminal)

        input_field = WrappedInput()
        menu = CompletionMenuComponent()

        def provider(text: str) -> list[tuple[str, str | None]]:
            if text.startswith("/"):
                return [("/cmd", "Command")]
            return []

        input_field.with_completion_component(provider, menu, trigger="/")
        tui.add_child(menu)
        tui.add_child(input_field)

        # Open menu
        input_field.set_value("/")
        for hook in input_field._post_input_hooks:
            hook()

        lines = tui.render(80)
        assert any("┌" in line for line in lines)  # Menu visible

        # Clear input
        input_field.set_value("")
        for hook in input_field._post_input_hooks:
            hook()

        lines = tui.render(80)
        assert not any("┌" in line for line in lines)  # Menu hidden
