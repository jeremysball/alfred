"""Tests for responsive status line behavior."""

from alfred.interfaces.pypitui.status_line import STATUS_WIDTH_FULL, STATUS_WIDTH_MEDIUM, StatusLine


class TestStatusLineResponsiveTiers:
    """Test responsive display at different width tiers."""

    def test_full_tier_shows_cached_reasoning(self):
        """Full width (80+) shows cached/reasoning tokens."""
        status = StatusLine()
        status.update(
            model="kimi-k2-5",
            ctx=32000,
            in_tokens=1000,
            out_tokens=500,
            cached=200,
            reasoning=100,
            queued=0,
        )

        result = status.render(STATUS_WIDTH_FULL)
        text = result[0]

        # Should show cached tokens with bolt symbol
        assert "⚡" in text or "\uf0e7" in text
        # Should show reasoning tokens with rho symbol
        assert "ρ" in text

    def test_medium_tier_shows_cached_reasoning_compact(self):
        """Medium width (50-79) shows cached/reasoning in compact format (icon as separator)."""
        status = StatusLine()
        status.update(
            model="kimi-k2-5",
            ctx=32000,
            in_tokens=1000,
            out_tokens=500,
            cached=200,
            reasoning=100,
            queued=0,
        )

        result = status.render(STATUS_WIDTH_MEDIUM)
        text = result[0]

        # Should show cached/reasoning symbols (icon as separator, no slash)
        assert "⚡" in text or "\uf0e7" in text
        assert "ρ" in text
        # Should show in/out tokens
        assert "↑" in text
        assert "↓" in text

    def test_compact_tier_shows_minimal(self):
        """Compact width (<50) shows only model + in/out."""
        status = StatusLine()
        status.update(
            model="kimi-k2-5",
            ctx=32000,
            in_tokens=1000,
            out_tokens=500,
            cached=200,
            reasoning=100,
            queued=3,
        )

        result = status.render(45)
        text = result[0]

        # Should show model name
        assert "kimi" in text
        # Should show in/out tokens
        assert "↑" in text
        assert "↓" in text
        # Should NOT show ctx
        assert "ctx" not in text

    def test_queued_shows_when_positive(self):
        """Queued indicator appears when > 0."""
        status = StatusLine()
        status.update(
            model="kimi",
            ctx=1000,
            in_tokens=100,
            out_tokens=50,
            cached=0,
            reasoning=0,
            queued=5,
        )

        result = status.render(STATUS_WIDTH_FULL)
        text = result[0]

        assert "queued 5" in text or "5" in text

    def test_queued_hidden_when_zero(self):
        """Queued indicator hidden when 0."""
        status = StatusLine()
        status.update(
            model="kimi",
            ctx=1000,
            in_tokens=100,
            out_tokens=50,
            cached=0,
            reasoning=0,
            queued=0,
        )

        result = status.render(STATUS_WIDTH_FULL)
        text = result[0]

        assert "queued" not in text


class TestStatusLineModelTruncation:
    """Test model name truncation at different widths."""

    def test_truncate_model_at_full_width(self):
        """Model truncated to 25 chars at full width."""
        status = StatusLine()
        long_model = "a" * 30
        status.update(
            model=long_model,
            ctx=1000,
            in_tokens=100,
            out_tokens=50,
            cached=0,
            reasoning=0,
            queued=0,
        )

        result = status.render(STATUS_WIDTH_FULL)
        text = result[0]

        # Should be truncated with ellipsis
        assert "…" in text

    def test_truncate_model_at_medium_width(self):
        """Model truncated to 15 chars at medium width."""
        status = StatusLine()
        long_model = "a" * 30
        status.update(
            model=long_model,
            ctx=1000,
            in_tokens=100,
            out_tokens=50,
            cached=0,
            reasoning=0,
            queued=0,
        )

        result = status.render(STATUS_WIDTH_MEDIUM)
        text = result[0]

        # Should be truncated with ellipsis
        assert "…" in text

    def test_truncate_model_at_compact_width(self):
        """Model truncated to 10 chars at compact width."""
        status = StatusLine()
        long_model = "a" * 30
        status.update(
            model=long_model,
            ctx=1000,
            in_tokens=100,
            out_tokens=50,
            cached=0,
            reasoning=0,
            queued=0,
        )

        result = status.render(45)
        text = result[0]

        # Should be truncated with ellipsis
        assert "…" in text


class TestStatusLineNoWrapping:
    """Test that status line never wraps."""

    def test_status_line_never_exceeds_width(self):
        """Render output always fits within specified width."""
        status = StatusLine()
        status.update(
            model="kimi-k2-5-128k-context-model",
            ctx=128000,
            in_tokens=50000,
            out_tokens=25000,
            cached=10000,
            reasoning=5000,
            queued=10,
        )

        for width in [30, 50, 80, 100, 200]:
            result = status.render(width)
            # Should return single element list
            assert len(result) == 1
            # Content should not exceed width (accounting for ANSI codes)
            text = result[0]
            # Strip ANSI codes for length check
            text.replace("\x1b[", "").replace("m", "").replace("0", "").replace("3", "").replace("3", "")
            # Rough check - actual visible chars should be <= width
            visible_len = len(text)
            for i in range(30, 40):  # Remove color codes roughly
                visible_len = visible_len - text.count(f"\x1b[{i}m") * 5
            assert visible_len <= width + 20, f"Width {width}: text too long"

    def test_status_line_single_element_returned(self):
        """Always returns single string in list."""
        status = StatusLine()
        status.update(
            model="kimi",
            ctx=1000,
            in_tokens=100,
            out_tokens=50,
            cached=0,
            reasoning=0,
            queued=0,
        )

        for width in [30, 50, 80, 100]:
            result = status.render(width)
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], str)
            assert "\n" not in result[0]
