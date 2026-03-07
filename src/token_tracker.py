"""Token usage tracking for Alfred conversations."""

from dataclasses import dataclass

from src.type_defs import UsageData


@dataclass
class TokenUsage:
    """Cumulative token usage for a conversation."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    reasoning_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary for serialization."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "reasoning_tokens": self.reasoning_tokens,
        }


class TokenTracker:
    """Tracks cumulative token usage across a conversation.

    Accumulates usage data from LLM responses to provide running totals.
    Used by the CLI status line to display token consumption.
    """

    def __init__(self) -> None:
        self._usage = TokenUsage()
        self._context_tokens: int = 0

    @property
    def usage(self) -> TokenUsage:
        """Get current cumulative usage."""
        return self._usage

    @property
    def context_tokens(self) -> int:
        """Get current context window size."""
        return self._context_tokens

    def add(self, usage: UsageData) -> None:
        """Add usage from an LLM response.

        Args:
            usage: Usage dict from LLM response containing:
                - prompt_tokens: Input tokens (required)
                - completion_tokens: Output tokens (required)
                - prompt_tokens_details.cached_tokens: Cache read tokens (optional)
                - completion_tokens_details.reasoning_tokens: Reasoning tokens (optional)
        """
        prompt_tokens = usage.get("prompt_tokens")
        if isinstance(prompt_tokens, int):
            self._usage.input_tokens += prompt_tokens

        completion_tokens = usage.get("completion_tokens")
        if isinstance(completion_tokens, int):
            self._usage.output_tokens += completion_tokens

        # Cached tokens (optional - from prompt_tokens_details)
        prompt_details = usage.get("prompt_tokens_details")
        if isinstance(prompt_details, dict):
            cached_tokens = prompt_details.get("cached_tokens")
            if isinstance(cached_tokens, int):
                self._usage.cache_read_tokens += cached_tokens

        # Reasoning tokens (optional - from completion_tokens_details)
        completion_details = usage.get("completion_tokens_details")
        if isinstance(completion_details, dict):
            reasoning_tokens = completion_details.get("reasoning_tokens")
            if isinstance(reasoning_tokens, int):
                self._usage.reasoning_tokens += reasoning_tokens

    def set_context_tokens(self, count: int) -> None:
        """Update current context window size.

        Args:
            count: Number of tokens in current context
        """
        self._context_tokens = count

    def reset(self) -> None:
        """Reset all counters for a new conversation."""
        self._usage = TokenUsage()
        self._context_tokens = 0

    def __repr__(self) -> str:
        return (
            f"TokenTracker(input={self._usage.input_tokens}, "
            f"output={self._usage.output_tokens}, "
            f"cache={self._usage.cache_read_tokens}, "
            f"reasoning={self._usage.reasoning_tokens}, "
            f"context={self._context_tokens})"
        )
