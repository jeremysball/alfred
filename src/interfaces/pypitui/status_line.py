"""StatusLine component for displaying model and token info."""

from pypitui import Component

from src.interfaces.pypitui.constants import DIM, RESET, YELLOW
from src.interfaces.pypitui.utils import format_tokens


class StatusLine(Component):
    """Status line showing model name and token usage.

    Format: model | ctx N in N out N | cached N reasoning N | queued N

    - ctx: context tokens (hidden if 0)
    - in/out: cumulative session tokens (always shown)
    - cached/reasoning: optional (hidden if 0)
    - queued: messages waiting to be sent (hidden if 0)
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
        self._exit_hint: bool = False

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
        exit_hint: bool = False,
        queued: int = 0,
    ) -> None:
        """Update all status values.

        Args:
            model: Model name (e.g., "kimi/moonshot-v1")
            ctx: Context window tokens
            in_tokens: Cumulative input tokens
            out_tokens: Cumulative output tokens
            cached: Cache read tokens
            reasoning: Reasoning tokens
            exit_hint: Show Ctrl-C exit hint
            queued: Number of queued messages
        """
        self._model = model
        self._ctx = ctx
        self._in = in_tokens
        self._out = out_tokens
        self._cached = cached
        self._reasoning = reasoning
        self._exit_hint = exit_hint
        self._queued = queued

    def render(self, width: int) -> list[str]:
        """Render status line.

        Args:
            width: Terminal width

        Returns:
            Single-element list with status line string
        """
        parts: list[str] = []

        # Group 1: model name
        parts.append(self._model)

        # Group 2: tokens (always show in/out)
        token_parts: list[str] = []
        if self._ctx > 0:
            token_parts.append(f"ctx {format_tokens(self._ctx)}")
        token_parts.append(f"in {format_tokens(self._in)}")
        token_parts.append(f"out {format_tokens(self._out)}")
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

        # Exit hint
        if self._exit_hint:
            parts.append(f"{DIM}Press Ctrl-C again to exit{RESET}")

        return [" | ".join(parts)]
