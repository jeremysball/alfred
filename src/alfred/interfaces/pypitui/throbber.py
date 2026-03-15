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
            (0, 255, 255),  # Bright cyan
            (50, 255, 255),  # Cyan
            (100, 255, 255),  # Light cyan
            (150, 255, 255),  # Pale cyan
            (200, 255, 255),  # White-cyan
            (255, 255, 255),  # White (peak)
            (200, 255, 255),  # White-cyan
            (150, 255, 255),  # Pale cyan
            (100, 255, 255),  # Light cyan
            (50, 255, 255),  # Cyan
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
            (50, 100, 200),  # Dark blue
        ],
        spin_rate=12.0,
    ),
    "neon": ThrobberStyle(
        name="neon",
        frames=["◉", "◎", "◍", "○", "◍", "◎"],
        colors=[
            (255, 0, 128),  # Hot pink
            (255, 50, 150),  # Pink
            (255, 100, 180),  # Light pink
            (200, 200, 200),  # White
            (255, 100, 180),  # Light pink
            (255, 50, 150),  # Pink
        ],
        spin_rate=8.0,
    ),
    "matrix": ThrobberStyle(
        name="matrix",
        frames=["ｱ", "ﾊ", "ﾐ", "ﾋ", "ｰ", "ｳ", "ｼ", "ﾅ", "ﾓ", "ﾆ", "ｻ", "ﾜ"],
        colors=[
            (0, 255, 0),  # Bright green
            (50, 255, 50),  # Green
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
            (255, 180, 80),  # Orange-gold
            (255, 160, 60),  # Orange
            (255, 140, 40),  # Dark orange
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
            (255, 0, 0),  # Red
            (0, 255, 0),  # Green
            (0, 0, 255),  # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
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
            (255, 200, 50),  # Orange-gold
            (200, 150, 30),  # Bronze
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
    # NERD FONT STYLES (require Nerd Font installed)
    # Verified working via Playwright screenshot testing
    "spinner": ThrobberStyle(
        name="spinner",
        frames=["\uf110"],  # fa-spinner
        colors=[
            (0, 255, 255),  # Cyan
            (50, 255, 200),  # Teal
            (100, 255, 150),  # Green-cyan
            (150, 255, 100),  # Lime
        ],
        spin_rate=8.0,
    ),
    "circle-notch": ThrobberStyle(
        name="circle-notch",
        frames=["\uf1ce"],  # fa-circle-notch
        colors=[
            (255, 0, 128),  # Hot pink
            (255, 50, 150),  # Pink
            (255, 100, 180),  # Light pink
            (255, 150, 200),  # Pale pink
        ],
        spin_rate=8.0,
    ),
    "bolt": ThrobberStyle(
        name="bolt",
        frames=["\uf0e7"],  # fa-bolt
        colors=[
            (255, 255, 0),  # Yellow
            (255, 200, 0),  # Gold
            (255, 150, 0),  # Orange
            (255, 100, 0),  # Dark orange
        ],
        spin_rate=10.0,
    ),
    "cog": ThrobberStyle(
        name="cog",
        frames=["\uf013"],  # fa-cog
        colors=[
            (150, 150, 150),  # Silver
            (180, 180, 180),  # Light gray
            (210, 210, 210),  # Very light
            (180, 180, 180),  # Light gray
        ],
        spin_rate=6.0,
    ),
    "chip": ThrobberStyle(
        name="chip",
        frames=["\uf2db"],  # fa-microchip
        colors=[
            (100, 200, 255),  # Blue
            (100, 255, 100),  # Green
            (255, 255, 100),  # Yellow
            (255, 200, 100),  # Orange
        ],
        spin_rate=8.0,
    ),
    "wifi": ThrobberStyle(
        name="wifi",
        frames=["\uf1eb"],  # fa-wifi
        colors=[
            (0, 255, 0),  # Green
            (100, 255, 100),  # Light green
            (200, 255, 200),  # Pale green
        ],
        spin_rate=6.0,
    ),
    "database": ThrobberStyle(
        name="database",
        frames=["\uf1c0"],  # fa-database
        colors=[
            (100, 150, 255),  # Blue
            (150, 100, 255),  # Purple
            (255, 100, 200),  # Pink
        ],
        spin_rate=6.0,
    ),
    "sync": ThrobberStyle(
        name="sync",
        frames=["\uf021"],  # fa-sync
        colors=[
            (255, 200, 100),  # Gold
            (255, 255, 100),  # Yellow
            (200, 255, 100),  # Lime
        ],
        spin_rate=8.0,
    ),
    # EMOJI STYLE
    "cat": ThrobberStyle(
        name="cat",
        frames=["🐱", "😺", "😸", "😹", "😻", "🙀"],
        colors=[
            (255, 200, 100),  # Orange
            (255, 180, 80),  # Light orange
            (255, 160, 60),  # Peach
            (255, 140, 40),  # Dark orange
            (255, 120, 20),  # Red-orange
            (255, 100, 0),  # Red
        ],
        spin_rate=8.0,
    ),
    # HIGH-QUALITY RESEARCHED STYLES
    # Moon phases - meditative, astronomical
    "moon": ThrobberStyle(
        name="moon",
        frames=["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"],
        colors=[
            (100, 100, 100),  # Dark gray
            (150, 150, 150),  # Gray
            (200, 200, 200),  # Light gray
            (220, 220, 220),  # Very light
            (255, 255, 255),  # Full moon white
            (220, 220, 220),  # Very light
            (200, 200, 200),  # Light gray
            (150, 150, 150),  # Gray
        ],
        spin_rate=8.0,
    ),
    # Earth rotation - environmental, global
    "earth": ThrobberStyle(
        name="earth",
        frames=["🌍", "🌎", "🌏"],
        colors=[
            (100, 150, 255),  # Blue ocean
            (100, 200, 100),  # Green land
            (150, 220, 255),  # Light blue
        ],
        spin_rate=6.0,
    ),
    # Hearts - emotional, warm
    "hearts": ThrobberStyle(
        name="hearts",
        frames=["💛", "💙", "💜", "💚", "❤️", "💖"],
        colors=[
            (255, 255, 0),  # Yellow
            (100, 150, 255),  # Blue
            (200, 100, 255),  # Purple
            (100, 255, 100),  # Green
            (255, 50, 50),  # Red
            (255, 150, 200),  # Pink
        ],
        spin_rate=10.0,
    ),
    # Clock - time, precision
    "clock": ThrobberStyle(
        name="clock",
        frames=["🕛", "🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚"],
        colors=[
            (255, 200, 100),  # Gold
        ],
        spin_rate=12.0,
    ),
    # Rocket - launch, startup (Nerd Font)
    "rocket": ThrobberStyle(
        name="rocket",
        frames=["🚀", "✦", "·", "✧", "·"],
        colors=[
            (255, 100, 100),  # Red rocket
            (255, 200, 100),  # Gold sparkle
            (150, 150, 150),  # Gray trail
            (200, 200, 255),  # Blue sparkle
            (150, 150, 150),  # Gray trail
        ],
        spin_rate=10.0,
    ),
    # Snow - winter, calm (Nerd Font snowflake)
    "snow": ThrobberStyle(
        name="snow",
        frames=["❄️", "❅", "❆", "·"],
        colors=[
            (200, 240, 255),  # Light blue-white
            (220, 250, 255),  # Very light blue
            (255, 255, 255),  # White
            (150, 200, 220),  # Blue-gray
        ],
        spin_rate=6.0,
    ),
    # Toggle - minimal, elegant
    "toggle": ThrobberStyle(
        name="toggle",
        frames=["⊶", "⊷"],
        colors=[
            (150, 150, 150),  # Gray
            (255, 255, 255),  # White
        ],
        spin_rate=8.0,
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
