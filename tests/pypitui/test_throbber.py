"""Tests for Throbber animation component."""

import time

from alfred.interfaces.pypitui.throbber import ASCII_FRAMES, BRAILLE_FRAMES, Throbber


class TestThrobberConstants:
    """Test throbber frame constants."""

    def test_braille_frames_has_10_frames(self) -> None:
        """Braille animation should have 10 frames."""
        assert len(BRAILLE_FRAMES) == 10

    def test_ascii_frames_has_4_frames(self) -> None:
        """ASCII animation should have 4 frames."""
        assert len(ASCII_FRAMES) == 4

    def test_braille_frames_are_single_char(self) -> None:
        """Each braille frame should be a single character."""
        for frame in BRAILLE_FRAMES:
            assert len(frame) == 1

    def test_ascii_frames_are_single_char(self) -> None:
        """Each ASCII frame should be a single character."""
        for frame in ASCII_FRAMES:
            assert len(frame) == 1


class TestThrobberInit:
    """Test Throbber initialization."""

    def test_throbber_default_uses_braille(self) -> None:
        """Default throbber should use braille frames."""
        throbber = Throbber()
        assert throbber._frames == BRAILLE_FRAMES

    def test_throbber_can_use_ascii(self) -> None:
        """Throbber with use_braille=False should use ASCII frames."""
        throbber = Throbber(use_braille=False)
        assert throbber._frames == ASCII_FRAMES

    def test_throbber_index_starts_at_zero(self) -> None:
        """Throbber index should start at 0."""
        throbber = Throbber()
        assert throbber._index == 0


class TestThrobberRender:
    """Test Throbber render method."""

    def test_throbber_render_returns_frame(self) -> None:
        """Render should return current frame."""
        throbber = Throbber()
        result = throbber.render()
        assert result == BRAILLE_FRAMES[0]

    def test_throbber_render_after_tick(self) -> None:
        """Render should return next frame after tick."""
        throbber = Throbber()
        # Use explicit timestamps to control delta time
        base_time = 1000.0
        throbber.tick(base_time)  # First tick advances (last_tick was 0)
        result = throbber.render()
        assert result == BRAILLE_FRAMES[1]


class TestThrobberTick:
    """Test Throbber tick method."""

    def test_throbber_tick_advances(self) -> None:
        """Tick should advance to next frame."""
        throbber = Throbber()
        assert throbber._index == 0
        throbber.tick(1000.0)  # First tick always advances (last_tick was 0)
        assert throbber._index == 1

    def test_throbber_tick_multiple_times(self) -> None:
        """Multiple ticks should advance through frames."""
        throbber = Throbber()
        base_time = 1000.0
        # First tick sets baseline
        throbber.tick(base_time)
        # Subsequent ticks need enough delta time
        for i in range(5):
            throbber.tick(base_time + (i + 1) * 1.0)  # 1 second between ticks
        assert throbber._index == 6  # 1 initial + 5 more

    def test_throbber_loops_at_end_braille(self) -> None:
        """Tick at last braille frame should wrap to first."""
        throbber = Throbber(use_braille=True)
        base_time = 1000.0
        # Move to last frame
        for i in range(10):
            throbber.tick(base_time + i * 1.0)
        assert throbber._index == 0  # Wrapped around

    def test_throbber_loops_at_end_ascii(self) -> None:
        """Tick at last ASCII frame should wrap to first."""
        throbber = Throbber(use_braille=False)
        base_time = 1000.0
        # Move to last frame and wrap
        for i in range(4):
            throbber.tick(base_time + i * 1.0)
        assert throbber._index == 0  # Wrapped around

    def test_throbber_tick_returns_true_on_change(self) -> None:
        """Tick should return True when frame changes."""
        throbber = Throbber()
        result = throbber.tick(1000.0)  # First tick always advances
        assert result is True

    def test_throbber_tick_returns_false_when_no_change(self) -> None:
        """Tick should return False when frame doesn't change."""
        throbber = Throbber(spin_rate=1.0)  # 1 frame per second
        base_time = 1000.0
        throbber.tick(base_time)  # First tick advances
        # Immediate second tick should not advance (delta < 1 second)
        result = throbber.tick(base_time + 0.1)  # Only 0.1s later
        assert result is False


class TestThrobberReset:
    """Test Throbber reset method."""

    def test_throbber_reset_sets_index_0(self) -> None:
        """Reset should set index back to 0."""
        throbber = Throbber()
        base_time = 1000.0
        throbber.tick(base_time)
        throbber.tick(base_time + 1.0)
        assert throbber._index == 2
        throbber.reset()
        assert throbber._index == 0

    def test_throbber_reset_render_returns_first_frame(self) -> None:
        """After reset, render should return first frame."""
        throbber = Throbber()
        base_time = 1000.0
        throbber.tick(base_time)
        throbber.tick(base_time + 1.0)
        throbber.reset()
        assert throbber.render() == BRAILLE_FRAMES[0]

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


class TestThrobberBrailleVsAscii:
    """Test differences between braille and ASCII modes."""

    def test_throbber_braille_vs_ascii_first_frame(self) -> None:
        """Braille and ASCII should have different first frames."""
        braille = Throbber(use_braille=True)
        ascii_throbber = Throbber(use_braille=False)
        assert braille.render() != ascii_throbber.render()

    def test_throbber_ascii_full_cycle(self) -> None:
        """ASCII throbber should cycle through all 4 frames."""
        throbber = Throbber(use_braille=False)
        base_time = 1000.0
        frames = []
        for i in range(5):
            frames.append(throbber.render())
            throbber.tick(base_time + i * 1.0)
        # After 4 ticks, should be back at start
        # First and last should match (full cycle)
        assert frames[0] == frames[4]
        # All 4 frames should be different
        assert len(set(frames[:4])) == 4


class TestThrobberDeltaTime:
    """Test throbber delta time behavior."""

    def test_throbber_slow_spin_rate_does_not_advance_immediately(self) -> None:
        """With slow spin rate, tick should not advance frame immediately."""
        throbber = Throbber(spin_rate=1.0)  # 1 frame per second
        initial_frame = throbber.render()
        base_time = 1000.0
        throbber.tick(base_time)  # First tick advances
        # Immediate second tick should not advance (within same frame time)
        throbber.tick(base_time + 0.1)  # Only 0.1s later
        assert throbber.render() == BRAILLE_FRAMES[1]  # Still on frame 1

    def test_throbber_returns_false_when_no_advance(self) -> None:
        """Tick should return False when delta time hasn't exceeded frame time."""
        throbber = Throbber(spin_rate=1.0)
        base_time = 1000.0
        throbber.tick(base_time)  # First tick
        result = throbber.tick(base_time + 0.1)  # Second tick immediately after
        assert result is False

    def test_throbber_spin_rate_affects_speed(self) -> None:
        """Higher spin rate should allow faster frame advancement."""
        # Fast spin rate: 10 frames per second
        fast_throbber = Throbber(spin_rate=10.0)
        base_time = 1000.0
        fast_throbber.tick(base_time)  # First tick
        result = fast_throbber.tick(base_time + 0.1)  # 0.1s later
        assert result is True  # Should advance (0.1s >= 0.1s frame time)

    def test_throbber_default_spin_rate_is_6fps(self) -> None:
        """Default spin rate should be 6 frames per second."""
        throbber = Throbber()
        assert throbber._spin_rate == 6.0
