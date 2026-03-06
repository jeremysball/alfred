"""Streaming throbber animation component.

Provides animated spinner for status line during LLM streaming.
Supports both braille (10 frames) and ASCII (4 frames) modes.
"""

BRAILLE_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
ASCII_FRAMES = ["|", "/", "-", "\\"]


class Throbber:
    """Animated throbber for streaming indicator.

    Usage:
        throbber = Throbber()
        # In render loop:
        throbber.tick()
        symbol = throbber.render()  # Returns current frame
    """

    def __init__(self, use_braille: bool = True) -> None:
        """Initialize throbber.

        Args:
            use_braille: If True, use braille animation (10 frames).
                        If False, use ASCII animation (4 frames).
        """
        self._frames = BRAILLE_FRAMES if use_braille else ASCII_FRAMES
        self._index = 0

    def tick(self) -> None:
        """Advance to next frame. Wraps at end."""
        self._index = (self._index + 1) % len(self._frames)

    def render(self) -> str:
        """Return current frame character."""
        return self._frames[self._index]

    def reset(self) -> None:
        """Reset to first frame."""
        self._index = 0
