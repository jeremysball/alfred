"""Streaming throbber animation component.

Provides animated spinner for status line during LLM streaming.
Supports both braille (10 frames) and ASCII (4 frames) modes.
"""

import time

BRAILLE_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
ASCII_FRAMES = ["|", "/", "-", "\\"]

# Default spin rate: 1 full rotation per second at 60fps = ~6 frames per second
DEFAULT_SPIN_RATE = 6.0  # frames per second


class Throbber:
    """Animated throbber for streaming indicator.

    Usage:
        throbber = Throbber()
        # In render loop (~60fps):
        throbber.tick()  # Uses delta time, spins at configured rate
        symbol = throbber.render()  # Returns current frame
    """

    def __init__(self, use_braille: bool = True, spin_rate: float = DEFAULT_SPIN_RATE) -> None:
        """Initialize throbber.

        Args:
            use_braille: If True, use braille animation (10 frames).
                        If False, use ASCII animation (4 frames).
            spin_rate: Animation speed in frames per second (default: 6.0).
                      Lower values = slower spin.
        """
        self._frames = BRAILLE_FRAMES if use_braille else ASCII_FRAMES
        self._index = 0
        self._spin_rate = spin_rate
        # Set _last_tick to 0 to ensure first tick always advances
        # This makes tests work and provides immediate feedback on first frame
        self._last_tick = 0.0

    def tick(self, now: float | None = None) -> bool:
        """Advance to next frame based on delta time.

        Args:
            now: Optional timestamp for testing. If None, uses time.monotonic().

        Returns:
            True if frame changed, False otherwise.
        """
        if now is None:
            now = time.monotonic()
        delta = now - self._last_tick

        # Time per frame = 1 / spin_rate
        frame_time = 1.0 / self._spin_rate

        if delta >= frame_time:
            self._index = (self._index + 1) % len(self._frames)
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        """Return current frame character."""
        return self._frames[self._index]

    def reset(self) -> None:
        """Reset to first frame."""
        self._index = 0
        self._last_tick = time.monotonic()
