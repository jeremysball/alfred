"""Tests for Throbber animation component."""

from alfred.interfaces.pypitui.throbber import (
    THROBBER_STYLES,
    Throbber,
    ThrobberStyle,
    list_throbber_styles,
)


class TestThrobberStyle:
    """Test ThrobberStyle dataclass."""

    def test_style_render_returns_string(self) -> None:
        """Render should return a string."""
        style = ThrobberStyle(name="test", frames=["a", "b", "c"])
        result = style.render(0)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_style_render_with_colors_includes_ansi(self) -> None:
        """Render with colors should include ANSI escape codes."""
        style = ThrobberStyle(name="test", frames=["a"], colors=[(255, 0, 0)])
        result = style.render(0)
        assert "\x1b[" in result  # ANSI escape sequence

    def test_style_render_without_colors_no_ansi(self) -> None:
        """Render without colors should not include ANSI codes."""
        style = ThrobberStyle(name="test", frames=["a"], colors=None)
        result = style.render(0)
        assert "\x1b[" not in result
        assert result == "a"

    def test_style_render_cycles_frames(self) -> None:
        """Render should cycle through frames."""
        style = ThrobberStyle(name="test", frames=["a", "b", "c"])
        assert style.render(0) == "a"
        assert style.render(1) == "b"
        assert style.render(2) == "c"
        assert style.render(3) == "a"  # Cycles back


class TestThrobberStylesRegistry:
    """Test predefined styles registry."""

    def test_styles_registry_has_multiple_styles(self) -> None:
        """Registry should have multiple predefined styles."""
        assert len(THROBBER_STYLES) >= 5

    def test_list_throbber_styles_returns_names(self) -> None:
        """list_throbber_styles should return style names."""
        names = list_throbber_styles()
        assert isinstance(names, list)
        assert len(names) == len(THROBBER_STYLES)
        assert "glow" in names
        assert "classic" in names

    def test_all_styles_have_name_and_frames(self) -> None:
        """All predefined styles should have required fields."""
        for name, style in THROBBER_STYLES.items():
            assert style.name == name
            assert len(style.frames) > 0
            assert all(isinstance(f, str) for f in style.frames)

    def test_all_styles_have_valid_spin_rate(self) -> None:
        """All predefined styles should have positive spin rate."""
        for style in THROBBER_STYLES.values():
            assert style.spin_rate > 0


class TestThrobberInit:
    """Test Throbber initialization."""

    def test_throbber_default_uses_glow_style(self) -> None:
        """Default throbber should use glow style."""
        throbber = Throbber()
        assert throbber._style.name == "glow"

    def test_throbber_can_use_specific_style(self) -> None:
        """Throbber can be initialized with specific style name."""
        throbber = Throbber(style="classic")
        assert throbber._style.name == "classic"

    def test_throbber_invalid_style_defaults_to_glow(self) -> None:
        """Invalid style name should default to glow."""
        throbber = Throbber(style="nonexistent")
        assert throbber._style.name == "glow"

    def test_throbber_can_use_custom_style(self) -> None:
        """Throbber can use custom ThrobberStyle."""
        custom = ThrobberStyle(name="custom", frames=["x", "y", "z"])
        throbber = Throbber(custom_style=custom)
        assert throbber._style.name == "custom"

    def test_throbber_index_starts_at_zero(self) -> None:
        """Throbber index should start at 0."""
        throbber = Throbber()
        assert throbber.current_index == 0

    def test_throbber_frame_count_matches_style(self) -> None:
        """frame_count should match style's frame count."""
        throbber = Throbber(style="ascii")
        assert throbber.frame_count == 4


class TestThrobberRender:
    """Test Throbber render method."""

    def test_throbber_render_returns_non_empty_string(self) -> None:
        """Render should return a non-empty string."""
        throbber = Throbber()
        result = throbber.render()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_throbber_render_changes_after_tick(self) -> None:
        """Render should return different result after tick advances."""
        throbber = Throbber()
        initial = throbber.render()
        throbber.tick(1000.0)  # Force tick
        after_tick = throbber.render()
        # Should be different (unless it's a 1-frame style, which none are)
        assert initial != after_tick or throbber.frame_count == 1


class TestThrobberTick:
    """Test Throbber tick method."""

    def test_throbber_tick_advances_index(self) -> None:
        """Tick should advance the frame index."""
        throbber = Throbber()
        initial_index = throbber.current_index
        throbber.tick(1000.0)  # First tick always advances
        assert throbber.current_index != initial_index

    def test_throbber_tick_multiple_times_advances(self) -> None:
        """Multiple ticks should advance through frames."""
        throbber = Throbber()
        base_time = 1000.0
        throbber.tick(base_time)
        initial = throbber.current_index
        # Tick enough to advance
        for i in range(5):
            throbber.tick(base_time + (i + 1) * 1.0)
        assert throbber.current_index != initial

    def test_throbber_loops_at_end(self) -> None:
        """Tick at last frame should wrap to first."""
        throbber = Throbber(style="ascii")  # 4 frames
        base_time = 1000.0
        initial = throbber.current_index
        # Tick through full cycle (frame_count ticks brings us back to start)
        for i in range(throbber.frame_count):
            throbber.tick(base_time + i * 1.0)
        # Should have wrapped back to initial
        assert throbber.current_index == initial

    def test_throbber_tick_returns_true_on_change(self) -> None:
        """Tick should return True when frame changes."""
        throbber = Throbber()
        result = throbber.tick(1000.0)  # First tick always advances
        assert result is True

    def test_throbber_tick_returns_false_when_no_change(self) -> None:
        """Tick should return False when frame doesn't change."""
        throbber = Throbber(custom_style=ThrobberStyle(name="slow", frames=["a", "b"], spin_rate=1.0))
        base_time = 1000.0
        throbber.tick(base_time)  # First tick advances
        # Immediate second tick should not advance
        result = throbber.tick(base_time + 0.1)
        assert result is False


class TestThrobberReset:
    """Test Throbber reset method."""

    def test_throbber_reset_sets_index_to_zero(self) -> None:
        """Reset should set index back to 0."""
        throbber = Throbber()
        base_time = 1000.0
        throbber.tick(base_time)
        throbber.tick(base_time + 1.0)
        assert throbber.current_index > 0
        throbber.reset()
        assert throbber.current_index == 0

    def test_throbber_reset_updates_last_tick(self) -> None:
        """Reset should update _last_tick to current time."""
        throbber = Throbber()
        base_time = 1000.0
        throbber.tick(base_time)
        # Manually set _last_tick to a known value
        throbber._last_tick = 500.0
        # Reset should update _last_tick
        throbber.reset()
        # _last_tick should be greater than the old value (updated to now)
        assert throbber._last_tick > 500.0


class TestThrobberDeltaTime:
    """Test throbber delta time behavior."""

    def test_throbber_respects_spin_rate(self) -> None:
        """Throbber should respect its spin rate for frame advancement."""
        slow_throbber = Throbber(style="ascii", custom_style=ThrobberStyle(name="slow", frames=["a", "b"], spin_rate=1.0))
        fast_throbber = Throbber(
            style="ascii",
            custom_style=ThrobberStyle(name="fast", frames=["a", "b"], spin_rate=10.0),
        )

        base_time = 1000.0

        # Both tick once
        slow_throbber.tick(base_time)
        fast_throbber.tick(base_time)

        # Fast throbber should advance with 0.1s delta
        fast_result = fast_throbber.tick(base_time + 0.1)
        assert fast_result is True

        # Slow throbber should not advance with 0.1s delta
        slow_result = slow_throbber.tick(base_time + 0.1)
        assert slow_result is False

    def test_throbber_fast_spin_rate_allows_quick_advance(self) -> None:
        """Higher spin rate should allow faster frame advancement."""
        throbber = Throbber(custom_style=ThrobberStyle(name="fast", frames=["a", "b"], spin_rate=20.0))
        base_time = 1000.0
        throbber.tick(base_time)
        # With 20 fps, frame time is 0.05s - use slightly more to avoid race conditions
        result = throbber.tick(base_time + 0.06)
        assert result is True


class TestThrobberDifferentStyles:
    """Test behavior across different styles."""

    def test_all_styles_can_tick_and_render(self) -> None:
        """All predefined styles should support tick and render."""
        for style_name in list_throbber_styles():
            throbber = Throbber(style=style_name)
            # Should be able to tick
            changed = throbber.tick(1000.0)
            assert changed is True
            # Should be able to render
            result = throbber.render()
            assert isinstance(result, str)
            assert len(result) > 0

    def test_all_styles_loop_correctly(self) -> None:
        """All styles should loop back to start after full cycle."""
        for style_name in list_throbber_styles():
            throbber = Throbber(style=style_name)
            base_time = 1000.0
            initial = throbber.current_index
            # Tick through full cycle
            for i in range(throbber.frame_count):
                throbber.tick(base_time + i * 1.0)
            # Should be back at start
            assert throbber.current_index == initial
