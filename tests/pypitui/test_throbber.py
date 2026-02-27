"""Tests for Throbber animation component."""

import pytest

from src.interfaces.pypitui.throbber import ASCII_FRAMES, BRAILLE_FRAMES, Throbber


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
        throbber.tick()
        result = throbber.render()
        assert result == BRAILLE_FRAMES[1]


class TestThrobberTick:
    """Test Throbber tick method."""

    def test_throbber_tick_advances(self) -> None:
        """Tick should advance to next frame."""
        throbber = Throbber()
        assert throbber._index == 0
        throbber.tick()
        assert throbber._index == 1

    def test_throbber_tick_multiple_times(self) -> None:
        """Multiple ticks should advance through frames."""
        throbber = Throbber()
        for _ in range(5):
            throbber.tick()
        assert throbber._index == 5

    def test_throbber_loops_at_end_braille(self) -> None:
        """Tick at last braille frame should wrap to first."""
        throbber = Throbber(use_braille=True)
        # Move to last frame
        for _ in range(9):
            throbber.tick()
        assert throbber._index == 9
        # Tick should wrap
        throbber.tick()
        assert throbber._index == 0

    def test_throbber_loops_at_end_ascii(self) -> None:
        """Tick at last ASCII frame should wrap to first."""
        throbber = Throbber(use_braille=False)
        # Move to last frame (index 3)
        for _ in range(3):
            throbber.tick()
        assert throbber._index == 3
        # Tick should wrap
        throbber.tick()
        assert throbber._index == 0


class TestThrobberReset:
    """Test Throbber reset method."""

    def test_throbber_reset_sets_index_0(self) -> None:
        """Reset should set index back to 0."""
        throbber = Throbber()
        throbber.tick()
        throbber.tick()
        assert throbber._index == 2
        throbber.reset()
        assert throbber._index == 0

    def test_throbber_reset_render_returns_first_frame(self) -> None:
        """After reset, render should return first frame."""
        throbber = Throbber()
        throbber.tick()
        throbber.tick()
        throbber.reset()
        assert throbber.render() == BRAILLE_FRAMES[0]


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
        frames = []
        for _ in range(4):
            frames.append(throbber.render())
            throbber.tick()
        # After 4 ticks, should be back at start
        frames.append(throbber.render())
        # First and last should match (full cycle)
        assert frames[0] == frames[4]
        # All 4 frames should be different
        assert len(set(frames[:4])) == 4
