"""Throbber design showcase - various animation concepts with glow/trail effects.

Each throbber class renders a sequence of ANSI-animated frames.
Usage: Instantiate and call render() in a loop, tick() to advance.
"""

import time
from abc import ABC, abstractmethod
from typing import List

# ANSI escape codes for effects
RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"

# ANSI 256-color palette (simplified glow gradients)
def rgb(r: int, g: int, b: int) -> str:
    """Return ANSI truecolor foreground code."""
    return f"\x1b[38;2;{r};{g};{b}m"


def bg_rgb(r: int, g: int, b: int) -> str:
    """Return ANSI truecolor background code."""
    return f"\x1b[48;2;{r};{g};{b}m"


# ============================================================================
# IDEA 1: COMET TRAIL
# ============================================================================
class CometThrobber:
    """A shooting star with fading tail.

    Visual: ●═══► (bright head, dimming trail)
    Best for: Sci-fi aesthetic, showing forward motion
    """

    TRAIL_CHARS = ["●", "◐", "◑", "○", "·", " "]
    TRAIL_COLORS = [
        (255, 255, 255),  # White hot
        (200, 220, 255),  # Blue-white
        (150, 180, 255),  # Light blue
        (100, 150, 255),  # Blue
        (50, 100, 200),   # Dark blue
        (30, 60, 120),    # Deep blue
    ]

    def __init__(self, tail_length: int = 5) -> None:
        self._pos = 0
        self._tail_length = tail_length
        self._last_tick = 0.0
        self._spin_rate = 10.0  # fps

    def tick(self, now: float | None = None) -> bool:
        if now is None:
            now = time.monotonic()
        delta = now - self._last_tick
        if delta >= 1.0 / self._spin_rate:
            self._pos = (self._pos + 1) % 8
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        """Render comet with colored trail."""
        # Build the comet: head + fading trail
        frames = []
        for i in range(self._tail_length):
            # Trail fades as it gets further from head
            intensity = max(0, len(self.TRAIL_COLORS) - i - 1)
            color = self.TRAIL_COLORS[min(i, len(self.TRAIL_COLORS) - 1)]
            char = self.TRAIL_CHARS[min(i, len(self.TRAIL_CHARS) - 1)]
            frames.append(f"{rgb(*color)}{char}{RESET}")
        return "".join(frames)


# ============================================================================
# IDEA 2: NEON PULSE
# ============================================================================
class NeonPulseThrobber:
    """A pulsing neon ring that expands and contracts.

    Visual: ◉ → ◎ → ○ → ◎ → ◉ (glowing center)
    Best for: Cyberpunk aesthetic, heartbeat feel
    """

    FRAMES = ["◉", "◎", "◍", "○", "◍", "◎"]
    COLORS = [
        (255, 0, 128),    # Hot pink
        (255, 50, 150),   # Pink
        (255, 100, 180),  # Light pink
        (200, 200, 200),  # White
        (255, 100, 180),  # Light pink
        (255, 50, 150),   # Pink
    ]

    def __init__(self) -> None:
        self._index = 0
        self._last_tick = 0.0
        self._spin_rate = 8.0

    def tick(self, now: float | None = None) -> bool:
        if now is None:
            now = time.monotonic()
        delta = now - self._last_tick
        if delta >= 1.0 / self._spin_rate:
            self._index = (self._index + 1) % len(self.FRAMES)
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        color = self.COLORS[self._index]
        char = self.FRAMES[self._index]
        # Add glow effect with bold
        return f"{BOLD}{rgb(*color)}{char}{RESET}"


# ============================================================================
# IDEA 3: MATRIX RAIN
# ============================================================================
class MatrixThrobber:
    """Falling characters like The Matrix.

    Visual: Random katakana/braille falling down
    Best for: Hacker aesthetic, data processing feel
    """

    FRAMES = ["ｱ", "ﾊ", "ﾐ", "ﾋ", "ｰ", "ｳ", "ｼ", "ﾅ", "ﾓ", "ﾆ", "ｻ", "ﾜ"]
    GREEN_GLOW = [
        (0, 255, 0),      # Bright green
        (50, 255, 50),    # Green
        (100, 255, 100),  # Light green
        (150, 255, 150),  # Pale green
    ]

    def __init__(self) -> None:
        self._index = 0
        self._last_tick = 0.0
        self._spin_rate = 12.0

    def tick(self, now: float | None = None) -> bool:
        if now is None:
            now = time.monotonic()
        delta = now - self._last_tick
        if delta >= 1.0 / self._spin_rate:
            self._index = (self._index + 1) % len(self.FRAMES)
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        char = self.FRAMES[self._index]
        # Cycle through green shades for glow effect
        color_idx = self._index % len(self.GREEN_GLOW)
        color = self.GREEN_GLOW[color_idx]
        return f"{rgb(*color)}{char}{RESET}"


# ============================================================================
# IDEA 4: ORBITAL DOT
# ============================================================================
class OrbitalThrobber:
    """A dot orbiting around a center point.

    Visual: ˚∘｡◦∘˚ (rotating ring of dots)
    Best for: Planetary, scientific aesthetic
    """

    # Orbital positions showing a dot moving in circle
    FRAMES = ["◐", "◓", "◑", "◒"]
    COLORS = [
        (255, 200, 100),  # Gold
        (255, 180, 80),   # Orange-gold
        (255, 160, 60),   # Orange
        (255, 140, 40),   # Dark orange
    ]

    def __init__(self) -> None:
        self._index = 0
        self._last_tick = 0.0
        self._spin_rate = 6.0

    def tick(self, now: float | None = None) -> bool:
        if now is None:
            now = time.monotonic()
        delta = now - self._last_tick
        if delta >= 1.0 / self._spin_rate:
            self._index = (self._index + 1) % len(self.FRAMES)
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        color = self.COLORS[self._index]
        char = self.FRAMES[self._index]
        return f"{rgb(*color)}{char}{RESET}"


# ============================================================================
# IDEA 5: WAVE PROPAGATION
# ============================================================================
class WaveThrobber:
    """A sine wave propagating outward.

    Visual: ∿∿∿ (flowing wave pattern)
    Best for: Audio, signal processing, fluid dynamics
    """

    FRAMES = ["▁", "▃", "▅", "▇", "█", "▇", "▅", "▃"]
    WAVE_COLORS = [
        (100, 200, 255),  # Cyan
        (120, 210, 255),
        (140, 220, 255),
        (160, 230, 255),
        (180, 240, 255),
        (160, 230, 255),
        (140, 220, 255),
        (120, 210, 255),
    ]

    def __init__(self) -> None:
        self._index = 0
        self._last_tick = 0.0
        self._spin_rate = 10.0

    def tick(self, now: float | None = None) -> bool:
        if now is None:
            now = time.monotonic()
        delta = now - self._last_tick
        if delta >= 1.0 / self._spin_rate:
            self._index = (self._index + 1) % len(self.FRAMES)
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        color = self.WAVE_COLORS[self._index]
        char = self.FRAMES[self._index]
        return f"{rgb(*color)}{char}{RESET}"


# ============================================================================
# IDEA 6: GLITCH EFFECT
# ============================================================================
class GlitchThrobber:
    """Random character switching with RGB color separation.

    Visual: Random symbols with color channel separation
    Best for: Cyberpunk, retro-tech aesthetic
    """

    GLITCH_CHARS = ["▓", "▒", "░", "█", "▀", "▄", "▌", "▐"]
    GLITCH_COLORS = [
        (255, 0, 0),      # Red
        (0, 255, 0),      # Green
        (0, 0, 255),      # Blue
        (255, 255, 0),    # Yellow
        (255, 0, 255),    # Magenta
        (0, 255, 255),    # Cyan
    ]

    def __init__(self) -> None:
        self._index = 0
        self._last_tick = 0.0
        self._spin_rate = 15.0  # Fast glitch

    def tick(self, now: float | None = None) -> bool:
        if now is None:
            now = time.monotonic()
        delta = now - self._last_tick
        if delta >= 1.0 / self._spin_rate:
            self._index = (self._index + 1) % len(self.GLITCH_CHARS)
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        char = self.GLITCH_CHARS[self._index]
        color = self.GLITCH_COLORS[self._index % len(self.GLITCH_COLORS)]
        return f"{rgb(*color)}{char}{RESET}"


# ============================================================================
# IDEA 7: PARTICLE TRAIL (THE WINNER!)
# ============================================================================
class ParticleTrailThrobber:
    """Multiple particles with fading trails - the ultimate glow effect.

    Visual: ✦✧·∙· (sparkles with particle trails)
    Best for: Premium feel, magical/tech fusion
    """

    # Core particle that moves through positions
    FRAMES = ["◆", "◇", "◈", "◉", "◎", "◉", "◈", "◇"]

    # Gold-to-white gradient for premium glow
    GLOW_COLORS = [
        (255, 255, 255),  # White core
        (255, 250, 200),  # Light gold
        (255, 240, 150),  # Gold
        (255, 220, 100),  # Dark gold
        (255, 200, 50),   # Orange-gold
        (200, 150, 30),   # Bronze
    ]

    def __init__(self) -> None:
        self._index = 0
        self._last_tick = 0.0
        self._spin_rate = 12.0

    def tick(self, now: float | None = None) -> bool:
        if now is None:
            now = time.monotonic()
        delta = now - self._last_tick
        if delta >= 1.0 / self._spin_rate:
            self._index = (self._index + 1) % len(self.FRAMES)
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        """Render with layered glow effect."""
        # Use the frame character with gradient color
        color_idx = self._index % len(self.GLOW_COLORS)
        color = self.GLOW_COLORS[color_idx]
        char = self.FRAMES[self._index]

        # Bold for extra glow
        return f"{BOLD}{rgb(*color)}{char}{RESET}"


# ============================================================================
# IDEA 8: LIQUID METAL
# ============================================================================
class LiquidMetalThrobber:
    """Mercury-like liquid morphing effect.

    Visual: Droplet shapes morphing organically
    Best for: Premium, fluid aesthetic
    """

    FRAMES = ["●", "◐", "◑", "◒", "◓", "◒", "◑", "◐"]
    METAL_COLORS = [
        (220, 220, 220),  # Silver
        (200, 200, 200),
        (180, 180, 180),
        (160, 160, 160),
        (140, 140, 140),
        (160, 160, 160),
        (180, 180, 180),
        (200, 200, 200),
    ]

    def __init__(self) -> None:
        self._index = 0
        self._last_tick = 0.0
        self._spin_rate = 8.0

    def tick(self, now: float | None = None) -> bool:
        if now is None:
            now = time.monotonic()
        delta = now - self._last_tick
        if delta >= 1.0 / self._spin_rate:
            self._index = (self._index + 1) % len(self.FRAMES)
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        color = self.METAL_COLORS[self._index]
        char = self.FRAMES[self._index]
        return f"{rgb(*color)}{char}{RESET}"


# ============================================================================
# RECOMMENDED: ENHANCED BRAILLE WITH GLOW
# ============================================================================
class GlowBrailleThrobber:
    """Enhanced version of the original with cyan glow effect.

    Visual: Rotating braille with color gradient
    Best for: Drop-in replacement, keeps accessibility
    """

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    # Cyan gradient for "thinking" glow
    CYAN_GLOW = [
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
    ]

    def __init__(self) -> None:
        self._index = 0
        self._last_tick = 0.0
        self._spin_rate = 10.0

    def tick(self, now: float | None = None) -> bool:
        if now is None:
            now = time.monotonic()
        delta = now - self._last_tick
        if delta >= 1.0 / self._spin_rate:
            self._index = (self._index + 1) % len(self.FRAMES)
            self._last_tick = now
            return True
        return False

    def render(self) -> str:
        color = self.CYAN_GLOW[self._index]
        char = self.FRAMES[self._index]
        return f"{BOLD}{rgb(*color)}{char}{RESET}"


# Demo function to visualize all throbbers
def demo_all_throbbers():
    """Run all throbbers side by side for comparison."""
    throbbers = [
        ("Comet", CometThrobber()),
        ("Neon", NeonPulseThrobber()),
        ("Matrix", MatrixThrobber()),
        ("Orbital", OrbitalThrobber()),
        ("Wave", WaveThrobber()),
        ("Glitch", GlitchThrobber()),
        ("Particle", ParticleTrailThrobber()),
        ("Liquid", LiquidMetalThrobber()),
        ("GlowBraille", GlowBrailleThrobber()),
    ]

    print("Throbber Showcase - Press Ctrl+C to stop\n")
    print(f"{'Name':<12} {'Animation':<20}")
    print("-" * 35)

    try:
        while True:
            for name, throbber in throbbers:
                throbber.tick()
            # Clear line and redraw
            print("\r", end="")
            for name, throbber in throbbers:
                print(f"{name:<12} {throbber.render()}  ", end="")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n" + RESET)


if __name__ == "__main__":
    demo_all_throbbers()
