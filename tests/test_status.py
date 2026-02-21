"""Tests for status line rendering."""

import pytest

from src.interfaces.status import SPINNER_FRAMES, StatusData, StatusRenderer
from src.token_tracker import TokenUsage


class TestStatusData:
    """Tests for StatusData dataclass."""

    def test_status_data_initialization(self) -> None:
        """StatusData initializes with all fields."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        status = StatusData(
            model_name="kimi/moonshot-v1-128k",
            usage=usage,
            context_tokens=500,
            is_streaming=True,
        )

        assert status.model_name == "kimi/moonshot-v1-128k"
        assert status.usage.input_tokens == 100
        assert status.usage.output_tokens == 50
        assert status.context_tokens == 500
        assert status.is_streaming is True

    def test_spinner_frame_when_streaming(self) -> None:
        """Spinner returns frames when streaming."""
        usage = TokenUsage()
        status = StatusData(
            model_name="test/model",
            usage=usage,
            context_tokens=0,
            is_streaming=True,
        )

        # Get several frames - should cycle through
        frames = [status.next_spinner_frame() for _ in range(15)]
        # All frames should be from the spinner
        assert all(f in SPINNER_FRAMES for f in frames)

    def test_spinner_frame_when_idle(self) -> None:
        """Spinner returns static dot when idle."""
        usage = TokenUsage()
        status = StatusData(
            model_name="test/model",
            usage=usage,
            context_tokens=0,
            is_streaming=False,
        )

        # Should always return idle indicator
        assert status.next_spinner_frame() == "●"
        assert status.next_spinner_frame() == "●"

    def test_spinner_transitions_to_idle(self) -> None:
        """Spinner transitions to idle when is_streaming changes."""
        usage = TokenUsage()
        status = StatusData(
            model_name="test/model",
            usage=usage,
            context_tokens=0,
            is_streaming=True,
        )

        # Get a streaming frame
        frame1 = status.next_spinner_frame()
        assert frame1 in SPINNER_FRAMES

        # Transition to idle
        status.is_streaming = False
        frame2 = status.next_spinner_frame()
        assert frame2 == "●"


class TestStatusRenderer:
    """Tests for StatusRenderer."""

    def test_render_basic(self) -> None:
        """Renderer produces text with model name and tokens."""
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        status = StatusData(
            model_name="kimi/moonshot-v1-128k",
            usage=usage,
            context_tokens=200,
            is_streaming=False,
        )
        renderer = StatusRenderer(status)
        text = renderer.render()

        # Check plain text contains expected elements
        plain = text.plain
        assert "kimi/moonshot-v1-128k" in plain
        assert "1.0K" in plain  # input tokens formatted
        assert "500" in plain  # output tokens
        assert "Context: 200" in plain

    def test_render_with_cache_and_reasoning(self) -> None:
        """Renderer includes cache and reasoning tokens when present."""
        usage = TokenUsage(
            input_tokens=2000,
            output_tokens=1000,
            cache_read_tokens=500,
            reasoning_tokens=200,
        )
        status = StatusData(
            model_name="test/model",
            usage=usage,
            context_tokens=300,
            is_streaming=False,
        )
        renderer = StatusRenderer(status)
        text = renderer.render()

        plain = text.plain
        assert "2.0K" in plain  # input
        assert "1.0K" in plain  # output
        assert "500" in plain  # cache
        assert "200" in plain  # reasoning

    def test_render_hides_zero_cache_and_reasoning(self) -> None:
        """Renderer omits cache/reasoning when zero."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=0,
            reasoning_tokens=0,
        )
        status = StatusData(
            model_name="test/model",
            usage=usage,
            context_tokens=100,
            is_streaming=False,
        )
        renderer = StatusRenderer(status)
        text = renderer.render()

        plain = text.plain
        # Should have input/output but not cache/reasoning labels
        assert "📥" in plain
        assert "📤" in plain
        # Cache/reasoning with zero values should not appear
        # (The emojis 💾 and 🧠 should not be in the output)

    def test_format_number_small(self) -> None:
        """Numbers under 1000 are not abbreviated."""
        assert StatusRenderer._format_number(0) == "0"
        assert StatusRenderer._format_number(500) == "500"
        assert StatusRenderer._format_number(999) == "999"

    def test_format_number_thousands(self) -> None:
        """Numbers 1000+ use K suffix."""
        assert StatusRenderer._format_number(1000) == "1.0K"
        assert StatusRenderer._format_number(1500) == "1.5K"
        assert StatusRenderer._format_number(12345) == "12.3K"

    def test_render_streaming_style(self) -> None:
        """Streaming state applies cyan color to spinner."""
        usage = TokenUsage()
        status = StatusData(
            model_name="test/model",
            usage=usage,
            context_tokens=0,
            is_streaming=True,
        )
        renderer = StatusRenderer(status)
        text = renderer.render()

        # First span should be cyan spinner
        assert len(text.spans) > 0
        first_span = text.spans[0]
        assert "cyan" in str(first_span.style)

    def test_render_idle_style(self) -> None:
        """Idle state applies green color to dot."""
        usage = TokenUsage()
        status = StatusData(
            model_name="test/model",
            usage=usage,
            context_tokens=0,
            is_streaming=False,
        )
        renderer = StatusRenderer(status)
        text = renderer.render()

        # First span should be green dot
        assert len(text.spans) > 0
        first_span = text.spans[0]
        assert "green" in str(first_span.style)
