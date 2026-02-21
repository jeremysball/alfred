"""Tests for TokenTracker."""

import pytest

from src.token_tracker import TokenTracker, TokenUsage


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_default_values(self) -> None:
        """Test default values are zero."""
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cache_read_tokens == 0
        assert usage.reasoning_tokens == 0

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=25,
            reasoning_tokens=10,
        )
        result = usage.to_dict()
        assert result == {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_tokens": 25,
            "reasoning_tokens": 10,
        }


class TestTokenTracker:
    """Tests for TokenTracker."""

    def test_initial_state(self) -> None:
        """Test tracker starts with zero values."""
        tracker = TokenTracker()
        assert tracker.usage.input_tokens == 0
        assert tracker.usage.output_tokens == 0
        assert tracker.usage.cache_read_tokens == 0
        assert tracker.usage.reasoning_tokens == 0
        assert tracker.context_tokens == 0

    def test_add_basic_usage(self) -> None:
        """Test adding basic usage (prompt + completion tokens)."""
        tracker = TokenTracker()
        tracker.add({
            "prompt_tokens": 100,
            "completion_tokens": 50,
        })
        assert tracker.usage.input_tokens == 100
        assert tracker.usage.output_tokens == 50
        assert tracker.usage.cache_read_tokens == 0
        assert tracker.usage.reasoning_tokens == 0

    def test_add_usage_with_cache(self) -> None:
        """Test adding usage with cached tokens."""
        tracker = TokenTracker()
        tracker.add({
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "prompt_tokens_details": {
                "cached_tokens": 80,
            },
        })
        assert tracker.usage.input_tokens == 100
        assert tracker.usage.output_tokens == 50
        assert tracker.usage.cache_read_tokens == 80

    def test_add_usage_with_reasoning(self) -> None:
        """Test adding usage with reasoning tokens."""
        tracker = TokenTracker()
        tracker.add({
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "completion_tokens_details": {
                "reasoning_tokens": 200,
            },
        })
        assert tracker.usage.input_tokens == 100
        assert tracker.usage.output_tokens == 50
        assert tracker.usage.reasoning_tokens == 200

    def test_add_usage_full(self) -> None:
        """Test adding complete usage data."""
        tracker = TokenTracker()
        tracker.add({
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "prompt_tokens_details": {
                "cached_tokens": 800,
            },
            "completion_tokens_details": {
                "reasoning_tokens": 300,
            },
        })
        assert tracker.usage.input_tokens == 1000
        assert tracker.usage.output_tokens == 500
        assert tracker.usage.cache_read_tokens == 800
        assert tracker.usage.reasoning_tokens == 300

    def test_accumulates_multiple_calls(self) -> None:
        """Test that multiple add() calls accumulate values."""
        tracker = TokenTracker()
        tracker.add({"prompt_tokens": 100, "completion_tokens": 50})
        tracker.add({"prompt_tokens": 200, "completion_tokens": 75})
        tracker.add({"prompt_tokens": 50, "completion_tokens": 25})

        assert tracker.usage.input_tokens == 350
        assert tracker.usage.output_tokens == 150

    def test_handles_missing_optional_fields(self) -> None:
        """Test handling when optional detail fields are missing."""
        tracker = TokenTracker()
        tracker.add({
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "prompt_tokens_details": None,
            "completion_tokens_details": None,
        })
        assert tracker.usage.cache_read_tokens == 0
        assert tracker.usage.reasoning_tokens == 0

    def test_handles_partial_detail_fields(self) -> None:
        """Test handling when detail dicts are missing specific keys."""
        tracker = TokenTracker()
        tracker.add({
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "prompt_tokens_details": {},  # No cached_tokens key
            "completion_tokens_details": {},  # No reasoning_tokens key
        })
        assert tracker.usage.cache_read_tokens == 0
        assert tracker.usage.reasoning_tokens == 0

    def test_set_context_tokens(self) -> None:
        """Test setting context token count."""
        tracker = TokenTracker()
        tracker.set_context_tokens(5000)
        assert tracker.context_tokens == 5000

    def test_context_tokens_updated(self) -> None:
        """Test context tokens can be updated multiple times."""
        tracker = TokenTracker()
        tracker.set_context_tokens(5000)
        tracker.set_context_tokens(7500)
        assert tracker.context_tokens == 7500

    def test_reset(self) -> None:
        """Test reset clears all values."""
        tracker = TokenTracker()
        tracker.add({
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "prompt_tokens_details": {"cached_tokens": 80},
            "completion_tokens_details": {"reasoning_tokens": 30},
        })
        tracker.set_context_tokens(5000)

        tracker.reset()

        assert tracker.usage.input_tokens == 0
        assert tracker.usage.output_tokens == 0
        assert tracker.usage.cache_read_tokens == 0
        assert tracker.usage.reasoning_tokens == 0
        assert tracker.context_tokens == 0

    def test_usage_property_returns_same_instance(self) -> None:
        """Test usage property returns current usage object."""
        tracker = TokenTracker()
        tracker.add({"prompt_tokens": 100, "completion_tokens": 50})

        usage = tracker.usage
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

        # Same instance - modifications affect tracker (intentional for internal use)
        assert usage is tracker.usage

    def test_repr(self) -> None:
        """Test string representation."""
        tracker = TokenTracker()
        tracker.add({"prompt_tokens": 100, "completion_tokens": 50})
        tracker.set_context_tokens(5000)

        repr_str = repr(tracker)
        assert "input=100" in repr_str
        assert "output=50" in repr_str
        assert "context=5000" in repr_str
