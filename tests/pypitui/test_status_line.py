"""Tests for StatusLine component."""


from src.interfaces.pypitui.status_line import (
    STATUS_WIDTH_COMPACT,
    STATUS_WIDTH_FULL,
    STATUS_WIDTH_MEDIUM,
    SYMBOL_CACHE,
    StatusLine,
)
from src.interfaces.pypitui.utils import format_tokens


class TestStatusLine:
    """Tests for StatusLine component (Phase 3)."""

    def test_status_line_renders_model_name(self):
        """Verify model name appears in output."""
        status = StatusLine()
        status.update(
            model="test-model",
            ctx=1000,
            in_tokens=500,
            out_tokens=100,
            cached=0,
            reasoning=0,
        )

        lines = status.render(width=80)
        assert len(lines) == 1
        assert "test-model" in lines[0]

    def test_status_line_shows_tokens(self):
        """Verify token counts appear in output with total/cached⚡ format."""
        status = StatusLine()
        status.update(
            model="test",
            ctx=1000,
            in_tokens=500,
            out_tokens=100,
            cached=50,
            reasoning=20,
        )

        lines = status.render(width=80)
        text = lines[0]
        assert "ctx 1K" in text
        # Input: total/cached⚡ format (500 total, 50 cached)
        assert f"↑500/50{SYMBOL_CACHE}" in text
        # Output: total/reasoningρ format (100 total, 20 reasoning)
        assert "↓100/20ρ" in text

    def test_status_line_hides_zero_values(self):
        """Verify ctx hidden when zero, plain format when no cached/reasoning."""
        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=500,
            out_tokens=100,
            cached=0,
            reasoning=0,
        )

        lines = status.render(width=80)
        text = lines[0]
        assert "ctx" not in text
        # Plain format when no cached/reasoning
        assert "↑500" in text
        assert "↓100" in text

    def test_status_full_width(self):
        """All groups shown at 80+ chars."""
        status = StatusLine()
        status.update(
            model="test-model",
            ctx=1000,
            in_tokens=500,
            out_tokens=100,
            cached=50,
            reasoning=20,
            queued=2,
        )

        lines = status.render(width=STATUS_WIDTH_FULL)
        text = lines[0]
        assert "test-model" in text
        assert "ctx 1K" in text
        # Input: total/cached⚡ (500 total, 50 cached)
        assert f"↑500/50{SYMBOL_CACHE}" in text
        # Output: total/reasoningρ
        assert "↓100/20ρ" in text
        assert "queued" in text

    def test_status_medium_width(self):
        """Model + tokens + queued at 50-79 chars."""
        status = StatusLine()
        status.update(
            model="test-model",
            ctx=1000,
            in_tokens=500,
            out_tokens=100,
            cached=50,
            reasoning=20,
            queued=2,
        )

        lines = status.render(width=STATUS_WIDTH_MEDIUM)
        text = lines[0]
        assert "test-model" in text
        assert "ctx 1K" in text
        # Input: ↑total⚡cached (compact format, icon as separator)
        # Output: ↓totalρreasoning (compact format, icon as separator)
        assert f"↑500{SYMBOL_CACHE}50" in text
        assert "↓100ρ20" in text
        assert "queued" in text

    def test_status_compact_width(self):
        """Short format at <50 chars."""
        status = StatusLine()
        status.update(
            model="very-long-model-name-here",
            ctx=1000,
            in_tokens=500,
            out_tokens=100,
            cached=50,
            reasoning=20,
            queued=2,
        )

        lines = status.render(width=STATUS_WIDTH_COMPACT)
        text = lines[0]
        assert "…" in text  # truncated
        # Input shows total/cached⚡ in compact
        assert f"↑500/50{SYMBOL_CACHE}" in text
        # Output shows just total (no reasoning) in compact
        assert "↓100" in text
        assert "ctx" not in text  # hidden at compact
        assert "queued" not in text  # just number shown

    def test_status_shows_queued(self):
        """queued count shown when > 0."""
        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=0,
            out_tokens=0,
            cached=0,
            reasoning=0,
            queued=3,
        )

        lines = status.render(width=80)
        assert "queued 3" in lines[0]

    def test_status_hides_queued_when_zero(self):
        """queued hidden when 0."""
        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=0,
            out_tokens=0,
            cached=0,
            reasoning=0,
            queued=0,
        )

        lines = status.render(width=80)
        assert "queued" not in lines[0]

    def test_status_truncates_long_model_name(self):
        """Very long model name truncated with ellipsis."""
        status = StatusLine()
        status.update(
            model="this-is-a-very-long-model-name-that-should-be-truncated",
            ctx=0,
            in_tokens=0,
            out_tokens=0,
            cached=0,
            reasoning=0,
        )

        lines = status.render(width=80)
        assert "…" in lines[0]
        assert "this-is-a-very-long-model-name-that-should-be-truncated" not in lines[0]

    def test_status_uses_arrow_symbols(self):
        """Verify arrow symbols used for in/out."""
        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=500,
            out_tokens=100,
            cached=0,
            reasoning=0,
        )

        lines = status.render(width=80)
        assert "↑" in lines[0]  # up arrow for input (to model)
        assert "↓" in lines[0]  # down arrow for output (from model)


class TestStatusLineThrobber:
    """Tests for StatusLine throbber integration (Phase 9)."""

    def test_status_shows_throbber_when_streaming(self) -> None:
        """Throbber character should appear when streaming=True."""
        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=500,
            out_tokens=100,
            cached=0,
            reasoning=0,
            streaming=True,
        )

        lines = status.render(width=80)
        # Throbber braille character should be first
        assert lines[0].startswith("⠋")

    def test_status_hides_throbber_when_not_streaming(self) -> None:
        """No throbber when streaming=False (default)."""
        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=500,
            out_tokens=100,
            cached=0,
            reasoning=0,
            streaming=False,
        )

        lines = status.render(width=80)
        # Should start with model name, not throbber
        assert lines[0].startswith("test")

    def test_throbber_position_before_model(self) -> None:
        """Throbber appears before model name."""
        status = StatusLine()
        status.update(
            model="my-model",
            ctx=0,
            in_tokens=0,
            out_tokens=0,
            cached=0,
            reasoning=0,
            streaming=True,
        )

        lines = status.render(width=80)
        text = lines[0]
        # Throbber first, then model
        throbber_idx = text.find("⠋")
        model_idx = text.find("my-model")
        assert throbber_idx < model_idx

    def test_throbber_shows_in_compact_mode(self) -> None:
        """Throbber visible even in compact layout."""
        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=500,
            out_tokens=100,
            cached=0,
            reasoning=0,
            streaming=True,
        )

        lines = status.render(width=STATUS_WIDTH_COMPACT)
        assert "⠋" in lines[0]

    def test_throbber_tick_advances(self) -> None:
        """tick_throbber() advances animation frame."""
        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=0,
            out_tokens=0,
            cached=0,
            reasoning=0,
            streaming=True,
        )

        # First frame
        lines1 = status.render(width=80)
        frame1 = lines1[0][0]

        # Tick to advance
        status.tick_throbber()

        # Second frame (should be different)
        lines2 = status.render(width=80)
        frame2 = lines2[0][0]

        # Frames should cycle (braille has 10 frames)
        # After 10 ticks, should be back to start
        assert frame1 == "⠋"
        assert frame2 == "⠙"

    def test_throbber_tick_ignored_when_not_streaming(self) -> None:
        """tick_throbber() does nothing when not streaming."""
        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=0,
            out_tokens=0,
            cached=0,
            reasoning=0,
            streaming=False,
        )

        # Should not crash
        status.tick_throbber()

        # Model should still be first
        lines = status.render(width=80)
        assert lines[0].startswith("test")


class TestFormatTokens:
    """Tests for format_tokens utility function."""

    def test_format_small_numbers(self):
        """Verify small numbers unchanged."""
        assert format_tokens(0) == "0"
        assert format_tokens(100) == "100"
        assert format_tokens(999) == "999"

    def test_format_thousands(self):
        """Verify thousands formatted with K."""
        assert format_tokens(1000) == "1K"
        assert format_tokens(1234) == "1.2K"
        assert format_tokens(10000) == "10K"
        assert format_tokens(12345) == "12.3K"

    def test_format_millions(self):
        """Verify millions formatted with M."""
        assert format_tokens(1_000_000) == "1M"
        assert format_tokens(1_234_567) == "1.2M"
        assert format_tokens(10_000_000) == "10M"
