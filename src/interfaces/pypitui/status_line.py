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
SYMBOL_REASONING = "ρ"  # U+03C1 GREEK SMALL LETTER RHO
# Cache symbol: Nerd Font fa-bolt (U+F0E7), displays as ⚡ fallback on non-Nerd fonts
SYMBOL_CACHE = "\uf0e7"  # Nerd Font fa-bolt


class StatusLine(Component):
    """Status line showing model name and token usage.

    Format: model | ctx N ↑in/cached⚡ ↓out/reasoningρ | queued N

    Token display when cached/reasoning tokens exist:
    - ↑500/50⚡ = 500 input tokens, 50 from cache
    - ↓100/20ρ = 100 output tokens, 20 were reasoning

    Responsive layout:
    - Full (80+): model | ctx | in/out | queued
    - Medium (50-79): model | ctx | in/out | queued
    - Compact (<50): model | in/out | queued

    Symbols:
    - ↑ for input tokens (sending to model)
    - ↓ for output tokens (receiving from model)
    - ⚡ for cached tokens (fa-bolt)
    - ρ for reasoning tokens
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
        # Strip provider prefix to save space
        model = self._model.replace("kimi/", "").replace("openai/", "")

        # Three tiers: full (25), medium (15), compact (10)
        if width >= STATUS_WIDTH_FULL:
            max_len = 25
        elif width >= STATUS_WIDTH_MEDIUM:
            max_len = 15
        else:
            max_len = 10

        if len(model) > max_len:
            return model[: max_len - 1] + "…"
        return model

    def _format_input_tokens(self, show_cache: bool = False) -> str:
        """Format input tokens.

        Args:
            show_cache: If True and cached > 0, show ↑total/cached⚡
                       If False or no cached, show ↑total
        """
        if show_cache and self._cached > 0:
            # ↑total/cached⚡ format
            in_str = format_tokens(self._in)
            cache_str = format_tokens(self._cached)
            return f"{SYMBOL_IN}{in_str}/{cache_str}{SYMBOL_CACHE}"
        return f"{SYMBOL_IN}{format_tokens(self._in)}"

    def _format_output_tokens(self, show_reasoning: bool = False) -> str:
        """Format output tokens.

        Args:
            show_reasoning: If True and reasoning > 0, show ↓total/reasoningρ
                           If False or no reasoning, show ↓total
        """
        if self._reasoning > 0 and show_reasoning:
            # ↓total/reasoningρ format
            out_str = format_tokens(self._out)
            reason_str = format_tokens(self._reasoning)
            return f"{SYMBOL_OUT}{out_str}/{reason_str}{SYMBOL_REASONING}"
        return f"{SYMBOL_OUT}{format_tokens(self._out)}"

    def _format_input_tokens_compact(self) -> str:
        """Format input tokens with icon as separator (compact).

        Format: ↑in⚡cached (no slash, icon acts as separator)
        """
        if self._cached > 0:
            in_str = format_tokens(self._in)
            cache_str = format_tokens(self._cached)
            return f"{SYMBOL_IN}{in_str}{SYMBOL_CACHE}{cache_str}"
        return f"{SYMBOL_IN}{format_tokens(self._in)}"

    def _format_output_tokens_compact(self) -> str:
        """Format output tokens with icon as separator (compact).

        Format: ↓outρreasoning (no slash, icon acts as separator)
        """
        if self._reasoning > 0:
            out_str = format_tokens(self._out)
            reason_str = format_tokens(self._reasoning)
            return f"{SYMBOL_OUT}{out_str}{SYMBOL_REASONING}{reason_str}"
        return f"{SYMBOL_OUT}{format_tokens(self._out)}"

    def _render_full(self) -> list[str]:
        """Render full layout (80+ chars)."""
        parts: list[str] = []

        # Group 2: tokens with arrows
        token_parts: list[str] = []
        if self._ctx > 0:
            token_parts.append(f"ctx {format_tokens(self._ctx)}")
        token_parts.append(self._format_input_tokens(show_cache=True))
        token_parts.append(self._format_output_tokens(show_reasoning=True))
        parts.append(" ".join(token_parts))

        # Group 3: queued messages (only if non-zero)
        if self._queued > 0:
            parts.append(f"{YELLOW}queued {self._queued}{RESET}")

        return parts

    def _render_medium(self) -> list[str]:
        """Render medium layout (50-79 chars)."""
        parts: list[str] = []

        # Group 2: tokens with arrows (compact format: icon as separator)
        token_parts: list[str] = []
        if self._ctx > 0:
            token_parts.append(f"ctx {format_tokens(self._ctx)}")
        token_parts.append(self._format_input_tokens_compact())
        token_parts.append(self._format_output_tokens_compact())
        parts.append(" ".join(token_parts))

        # Group 3: queued messages (only if non-zero)
        if self._queued > 0:
            parts.append(f"{YELLOW}queued {self._queued}{RESET}")

        return parts

    def _render_compact(self) -> list[str]:
        """Render compact layout (<50 chars)."""
        parts: list[str] = []

        # Just in/out with arrows (show bolt if cached)
        in_str = self._format_input_tokens(show_cache=True)
        out_str = self._format_output_tokens(show_reasoning=False)
        token_str = f"{in_str} {out_str}"
        parts.append(token_str)

        # Queued if present
        if self._queued > 0:
            parts.append(f"{YELLOW}{self._queued}{RESET}")

        return parts
