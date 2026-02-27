"""Tests for StatusLine component."""



class TestStatusLine:
    """Tests for StatusLine component (Phase 3)."""

    def test_status_line_renders_model_name(self):
        """Verify model name appears in output."""
        from src.interfaces.pypitui.status_line import StatusLine

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
        """Verify token counts appear in output."""
        from src.interfaces.pypitui.status_line import StatusLine

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
        assert "in 500" in text
        assert "out 100" in text
        assert "cached 50" in text
        assert "reasoning 20" in text

    def test_status_line_hides_zero_values(self):
        """Verify ctx, cached, reasoning hidden when zero."""
        from src.interfaces.pypitui.status_line import StatusLine

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
        assert "cached" not in text
        assert "reasoning" not in text
        # in/out always shown
        assert "in 500" in text
        assert "out 100" in text

    def test_status_line_exit_hint(self):
        """Verify exit hint appears when requested."""
        from src.interfaces.pypitui.status_line import StatusLine

        status = StatusLine()
        status.update(
            model="test",
            ctx=0,
            in_tokens=0,
            out_tokens=0,
            cached=0,
            reasoning=0,
            exit_hint=True,
        )

        lines = status.render(width=80)
        assert "Ctrl-C" in lines[0]


class TestFormatTokens:
    """Tests for format_tokens utility function."""

    def test_format_small_numbers(self):
        """Verify small numbers unchanged."""
        from src.interfaces.pypitui.utils import format_tokens

        assert format_tokens(0) == "0"
        assert format_tokens(100) == "100"
        assert format_tokens(999) == "999"

    def test_format_thousands(self):
        """Verify thousands formatted with K."""
        from src.interfaces.pypitui.utils import format_tokens

        assert format_tokens(1000) == "1K"
        assert format_tokens(1234) == "1.2K"
        assert format_tokens(10000) == "10K"
        assert format_tokens(12345) == "12.3K"

    def test_format_millions(self):
        """Verify millions formatted with M."""
        from src.interfaces.pypitui.utils import format_tokens

        assert format_tokens(1_000_000) == "1M"
        assert format_tokens(1_234_567) == "1.2M"
        assert format_tokens(10_000_000) == "10M"
