"""Tests for WrappedInput hook system."""

import pytest

from src.interfaces.pypitui.wrapped_input import WrappedInput


class TestInputHooks:
    """Test input filter hook system."""

    def test_add_input_hook_registers_callback(self) -> None:
        """add_input_hook stores the callback."""
        input_field = WrappedInput()
        
        def my_hook(key: str) -> bool:
            return False
        
        input_field.add_input_hook(my_hook)
        
        assert my_hook in input_field._input_hooks

    def test_input_filter_can_consume_key(self) -> None:
        """Filter returning True consumes the key."""
        input_field = WrappedInput()
        
        consumed_keys = []
        
        def consuming_hook(key: str) -> bool:
            consumed_keys.append(key)
            return True  # Consume the key
        
        input_field.add_input_hook(consuming_hook)
        input_field.handle_input("x")
        
        # Key was passed to filter
        assert "x" in consumed_keys
        # But not added to input value (consumed)
        assert input_field.get_value() == ""

    def test_input_filter_passes_through_when_false(self) -> None:
        """Filter returning False allows normal processing."""
        input_field = WrappedInput()
        
        def passing_hook(key: str) -> bool:
            return False  # Don't consume
        
        input_field.add_input_hook(passing_hook)
        input_field.handle_input("x")
        
        # Key was processed normally
        assert input_field.get_value() == "x"

    def test_multiple_filters_checked_in_order(self) -> None:
        """Multiple filters are checked until one consumes."""
        input_field = WrappedInput()
        
        order = []
        
        def hook1(key: str) -> bool:
            order.append(1)
            return False
        
        def hook2(key: str) -> bool:
            order.append(2)
            return True  # Consume
        
        def hook3(key: str) -> bool:
            order.append(3)
            return False
        
        input_field.add_input_hook(hook1)
        input_field.add_input_hook(hook2)
        input_field.add_input_hook(hook3)
        
        input_field.handle_input("x")
        
        # First two checked, third skipped (consumed by hook2)
        assert order == [1, 2]


class TestRenderHooks:
    """Test render filter hook system."""

    def test_add_render_hook_registers_callback(self) -> None:
        """add_render_hook stores the callback."""
        input_field = WrappedInput()
        
        def my_hook(lines: list[str], width: int) -> list[str]:
            return lines
        
        input_field.add_render_hook(my_hook)
        
        assert my_hook in input_field._render_hooks

    def test_render_filter_modifies_output(self) -> None:
        """Filter can transform rendered lines."""
        input_field = WrappedInput()
        input_field.set_value("test")
        
        def prefix_hook(lines: list[str], width: int) -> list[str]:
            return [">>> " + line for line in lines]
        
        input_field.add_render_hook(prefix_hook)
        lines = input_field.render(width=40)
        
        # All lines have prefix added
        for line in lines:
            assert line.startswith(">>> ")

    def test_multiple_render_hooks_applied_in_order(self) -> None:
        """Multiple filters are applied in registration order."""
        input_field = WrappedInput()
        input_field.set_value("x")
        
        def hook1(lines: list[str], width: int) -> list[str]:
            return [line + "A" for line in lines]
        
        def hook2(lines: list[str], width: int) -> list[str]:
            return [line + "B" for line in lines]
        
        input_field.add_render_hook(hook1)
        input_field.add_render_hook(hook2)
        
        lines = input_field.render(width=40)
        
        # Applied in order: first A, then B
        for line in lines:
            assert line.endswith("AB")


class TestHookIntegration:
    """Test filter integration with WrappedInput."""

    def test_filters_empty_by_default(self) -> None:
        """New WrappedInput has no filters."""
        input_field = WrappedInput()
        
        assert input_field._input_hooks == []
        assert input_field._render_hooks == []

    def test_input_filter_receives_all_keys(self) -> None:
        """Filter receives every key press."""
        input_field = WrappedInput()
        received = []
        
        def capture_hook(key: str) -> bool:
            received.append(key)
            return False
        
        input_field.add_input_hook(capture_hook)
        
        input_field.handle_input("a")
        input_field.handle_input("b")
        input_field.handle_input("c")
        
        assert received == ["a", "b", "c"]

    def test_render_filter_receives_width(self) -> None:
        """Filter receives the width parameter."""
        input_field = WrappedInput()
        received_width = None
        
        def capture_hook(lines: list[str], width: int) -> list[str]:
            nonlocal received_width
            received_width = width
            return lines
        
        input_field.add_render_hook(capture_hook)
        input_field.render(width=50)
        
        assert received_width == 50
