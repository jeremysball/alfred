"""Streaming throbber animation component.

Provides animated spinner for status line during LLM streaming.
Multiple animation styles with glow effects.
"""

import time
from dataclasses import dataclass

# ANSI escape codes
RESET = "\x1b[0m"
BOLD = "\x1b[1m"


def rgb(r: int, g: int, b: int) -> str:
    """Return ANSI truecolor foreground code."""
    return f"\x1b[38;2;{r};{g};{b}m"


@dataclass(frozen=True)
class ThrobberStyle:
    """Configuration for a throbber animation style."""

    name: str
    frames: list[str]
    colors: list[tuple[int, int, int]] | None = None
    spin_rate: float = 10.0
    use_bold: bool = True

    def render(self, index: int) -> str:
        """Render frame at given index with color."""
        char = self.frames[index % len(self.frames)]

        if self.colors:
            color = self.colors[index % len(self.colors)]
            prefix = BOLD if self.use_bold else ""
            return f"{prefix}{rgb(*color)}{char}{RESET}"

        return char


# Predefined animation styles
THROBBER_STYLES: dict[str, ThrobberStyle] = {
    "classic": ThrobberStyle(
        name="classic",
        frames=["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        colors=None,  # No color, plain braille
        spin_rate=10.0,
    ),
    "glow": ThrobberStyle(
        name="glow",
        frames=["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        colors=[
            (0, 255, 255),    # Bright cyan
            (50, 255, 255),   # Cyan
            (100, 255, 255),  # Light cyan
            (150, 255, 255),  # Pale cyan
            (200, 255, 255),  # White-cyan
            (255, 255, 255),  # White (peak)
            (200, 255, 255),  # White-cyan
            (150, 255, 255),  # Pale cyan
            (100, 255, 255),  # Light cyan
            (50, 255, 255),   # Cyan
        ],
        spin_rate=10.0,
    ),
    "comet": ThrobberStyle(
        name="comet",
        frames=["●", "◐", "◑", "○", "·"],
        colors=[
            (255, 255, 255),  # White hot
            (200, 220, 255),  # Blue-white
            (150, 180, 255),  # Light blue
            (100, 150, 255),  # Blue
            (50, 100, 200),   # Dark blue
        ],
        spin_rate=12.0,
    ),
    "neon": ThrobberStyle(
        name="neon",
        frames=["◉", "◎", "◍", "○", "◍", "◎"],
        colors=[
            (255, 0, 128),    # Hot pink
            (255, 50, 150),   # Pink
            (255, 100, 180),  # Light pink
            (200, 200, 200),  # White
            (255, 100, 180),  # Light pink
            (255, 50, 150),   # Pink
        ],
        spin_rate=8.0,
    ),
    "matrix": ThrobberStyle(
        name="matrix",
        frames=["ｱ", "ﾊ", "ﾐ", "ﾋ", "ｰ", "ｳ", "ｼ", "ﾅ", "ﾓ", "ﾆ", "ｻ", "ﾜ"],
        colors=[
            (0, 255, 0),      # Bright green
            (50, 255, 50),    # Green
            (100, 255, 100),  # Light green
            (150, 255, 150),  # Pale green
        ],
        spin_rate=12.0,
    ),
    "orbital": ThrobberStyle(
        name="orbital",
        frames=["◐", "◓", "◑", "◒"],
        colors=[
            (255, 200, 100),  # Gold
            (255, 180, 80),   # Orange-gold
            (255, 160, 60),   # Orange
            (255, 140, 40),   # Dark orange
        ],
        spin_rate=6.0,
    ),
    "wave": ThrobberStyle(
        name="wave",
        frames=["▁", "▃", "▅", "▇", "█", "▇", "▅", "▃"],
        colors=[
            (100, 200, 255),  # Cyan
            (120, 210, 255),
            (140, 220, 255),
            (160, 230, 255),
            (180, 240, 255),
            (160, 230, 255),
            (140, 220, 255),
            (120, 210, 255),
        ],
        spin_rate=10.0,
    ),
    "glitch": ThrobberStyle(
        name="glitch",
        frames=["▓", "▒", "░", "█", "▀", "▄", "▌", "▐"],
        colors=[
            (255, 0, 0),      # Red
            (0, 255, 0),      # Green
            (0, 0, 255),      # Blue
            (255, 255, 0),    # Yellow
            (255, 0, 255),    # Magenta
            (0, 255, 255),    # Cyan
        ],
        spin_rate=15.0,
    ),
    "particle": ThrobberStyle(
        name="particle",
        frames=["◆", "◇", "◈", "◉", "◎", "◉", "◈", "◇"],
        colors=[
            (255, 255, 255),  # White core
            (255, 250, 200),  # Light gold
            (255, 240, 150),  # Gold
            (255, 220, 100),  # Dark gold
            (255, 200, 50),   # Orange-gold
            (200, 150, 30),   # Bronze
        ],
        spin_rate=12.0,
    ),
    "liquid": ThrobberStyle(
        name="liquid",
        frames=["●", "◐", "◑", "◒", "◓", "◒", "◑", "◐"],
        colors=[
            (220, 220, 220),  # Silver
            (200, 200, 200),
            (180, 180, 180),
            (160, 160, 160),
            (140, 140, 140),
            (160, 160, 160),
            (180, 180, 180),
            (200, 200, 200),
        ],
        spin_rate=8.0,
    ),
    "ascii": ThrobberStyle(
        name="ascii",
        frames=["|", "/", "-", "\\"],
        colors=None,  # Plain ASCII
        spin_rate=6.0,
        use_bold=False,
    ),
}


class Throbber:
    """Animated throbber for streaming indicator.

    Usage:
        throbber = Throbber(style="glow")
        # In render loop (~60fps):
        throbber.tick()  # Uses delta time, spins at configured rate
        symbol = throbber.render()  # Returns current frame with effects
    """

    def __init__(
        self,
        style: str = "glow",
        custom_style: ThrobberStyle | None = None,
    ) -> None:
        """Initialize throbber.

        Args:
            style: Name of predefined style from THROBBER_STYLES.
                   Options: classic, glow, comet, neon, matrix, orbital,
                           wave, glitch, particle, liquid, ascii
            custom_style: Optional custom ThrobberStyle to override predefined.
        """
        if custom_style:
            self._style = custom_style
        elif style in THROBBER_STYLES:
            self._style = THROBBER_STYLES[style]
        else:
            self._style = THROBBER_STYLES["glow"]

        self._index = 0
        self._spin_rate = self._style.spin_rate
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

        frame_time = 1.0 / self._spin_rate

        if delta >= frame_time:
            self._index = (self._index + 1) % len(self._style.frames)
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        """Return current frame with styling applied."""
        return self._style.render(self._index)

    def reset(self) -> None:
        """Reset to first frame."""
        self._index = 0
        self._last_tick = time.monotonic()

    @property
    def frame_count(self) -> int:
        """Return number of frames in animation."""
        return len(self._style.frames)

    @property
    def current_index(self) -> int:
        """Return current frame index (for testing)."""
        return self._index


def list_throbber_styles() -> list[str]:
    """Return list of available throbber style names."""
    return list(THROBBER_STYLES.keys())
