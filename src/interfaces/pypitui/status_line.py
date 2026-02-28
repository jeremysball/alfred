"""StatusLine component for displaying model and token info."""

from pypitui import Component

from src.interfaces.pypitui.constants import RESET, YELLOW
from src.interfaces.pypitui.throbber import Throbber
from src.interfaces.pypitui.utils import format_tokens

# Width thresholds for responsive layout
STATUS_WIDTH_FULL = 80  # Show everything
STATUS_WIDTH_MEDIUM = 50  # Hide reasoning/cached
STATUS_WIDTH_COMPACT = 40  # Model + in/out only

# Arrow symbols (unicode fallback from nerd font)
# Input ↑ = sending to model, Output ↓ = receiving from model
SYMBOL_IN = "↑"  # U+2191 UPWARDS ARROW
SYMBOL_OUT = "↓"  # U+2193 DOWNWARDS ARROW


class StatusLine(Component):
    """Status line showing model name and token usage.

    Format: model | ctx N ↓N ↑N | cached N reasoning N | queued N

    Responsive layout:
    - Full (80+): model | ctx | in/out | cached/reasoning | queued
    - Medium (60-79): model | ctx | in/out | queued
    - Compact (<60): model | in/out

    Symbols:
    - ↑ for input tokens (sending to model)
    - ↓ for output tokens (receiving from model)
    """

    def __init__(self) -> None:
        """Initialize status line with empty state."""
        super().__init__()
        self._model: str = ""
        self._ctx: int = 0
        self._in: int = 0
        self._out: int = 0
        self._cached: int = 0
        self._reasoning: int = 0
        self._queued: int = 0
        self._is_streaming: bool = False
        self._throbber: Throbber = Throbber()

    def invalidate(self) -> None:
        """Mark this component as needing re-render."""
        # StatusLine is simple - no cached state to invalidate
        pass

    def update(
        self,
        model: str,
        ctx: int,
        in_tokens: int,
        out_tokens: int,
        cached: int,
        reasoning: int,
        queued: int = 0,
        streaming: bool = False,
    ) -> None:
        """Update all status values.

        Args:
            model: Model name (e.g., "kimi/moonshot-v1")
            ctx: Context window tokens
            in_tokens: Cumulative input tokens
            out_tokens: Cumulative output tokens
            cached: Cache read tokens
            reasoning: Reasoning tokens
            queued: Number of queued messages
            streaming: Show animated throbber during streaming
        """
        self._model = model
        self._ctx = ctx
        self._in = in_tokens
        self._out = out_tokens
        self._cached = cached
        self._reasoning = reasoning
        self._queued = queued
        self._is_streaming = streaming
        if not streaming:
            self._throbber.reset()

    def tick_throbber(self) -> None:
        """Advance throbber animation by one frame.

        Only animates when _is_streaming is True.
        """
        if self._is_streaming:
            self._throbber.tick()

    def render(self, width: int) -> list[str]:
        """Render status line.

        Args:
            width: Terminal width

        Returns:
            Single-element list with status line string
        """
        parts: list[str] = []

        # Throbber first if streaming
        if self._is_streaming:
            parts.append(self._throbber.render())

        # Truncate model name if needed
        model = self._truncate_model(width)

        # Group 1: model name
        parts.append(model)

        # Determine layout tier
        if width >= STATUS_WIDTH_FULL:
            parts.extend(self._render_full())
        elif width >= STATUS_WIDTH_MEDIUM:
            parts.extend(self._render_medium())
        else:
            parts.extend(self._render_compact())

        return [" | ".join(parts)]

    def _truncate_model(self, width: int) -> str:
        """Truncate model name based on available width.

        Args:
            width: Terminal width

        Returns:
            Truncated model name with ellipsis if needed
        """
        max_len = 25 if width >= STATUS_WIDTH_MEDIUM else 15
        if len(self._model) > max_len:
            return self._model[: max_len - 1] + "…"
        return self._model

    def _render_full(self) -> list[str]:
        """Render full layout (80+ chars)."""
        parts: list[str] = []

        # Group 2: tokens with arrows
        token_parts: list[str] = []
        if self._ctx > 0:
            token_parts.append(f"ctx {format_tokens(self._ctx)}")
        token_parts.append(f"{SYMBOL_IN}{format_tokens(self._in)}")
        token_parts.append(f"{SYMBOL_OUT}{format_tokens(self._out)}")
        parts.append(" ".join(token_parts))

        # Group 3: cached/reasoning (only if non-zero)
        cache_parts: list[str] = []
        if self._cached > 0:
            cache_parts.append(f"cached {format_tokens(self._cached)}")
        if self._reasoning > 0:
            cache_parts.append(f"reasoning {format_tokens(self._reasoning)}")
        if cache_parts:
            parts.append(" ".join(cache_parts))

        # Group 4: queued messages (only if non-zero)
        if self._queued > 0:
            parts.append(f"{YELLOW}queued {self._queued}{RESET}")

        return parts

    def _render_medium(self) -> list[str]:
        """Render medium layout (60-79 chars)."""
        parts: list[str] = []

        # Group 2: tokens with arrows
        token_parts: list[str] = []
        if self._ctx > 0:
            token_parts.append(f"ctx {format_tokens(self._ctx)}")
        token_parts.append(f"{SYMBOL_IN}{format_tokens(self._in)}")
        token_parts.append(f"{SYMBOL_OUT}{format_tokens(self._out)}")
        parts.append(" ".join(token_parts))

        # Group 3: queued messages (only if non-zero)
        if self._queued > 0:
            parts.append(f"{YELLOW}queued {self._queued}{RESET}")

        return parts

    def _render_compact(self) -> list[str]:
        """Render compact layout (<60 chars)."""
        parts: list[str] = []

        # Just in/out with arrows
        token_str = f"{SYMBOL_IN}{format_tokens(self._in)} {SYMBOL_OUT}{format_tokens(self._out)}"
        parts.append(token_str)

        # Queued if present
        if self._queued > 0:
            parts.append(f"{YELLOW}{self._queued}{RESET}")

        return parts
