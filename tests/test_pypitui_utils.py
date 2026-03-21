"""Tests for Alfred's PyPiTUI compatibility helpers."""

from alfred.interfaces.pypitui.utils import format_tokens, visible_width, wrap_text_with_ansi


def test_visible_width_ignores_ansi_and_counts_wide_characters() -> None:
    text = "A\x1b[31m😀\x1b[0mB"

    assert visible_width(text) == 4


def test_wrap_text_with_ansi_wraps_and_preserves_styles() -> None:
    text = "\x1b[31mabcdef\x1b[0m"

    lines = wrap_text_with_ansi(text, 3)

    assert lines == ["\x1b[31mabc\x1b[0m", "\x1b[31mdef\x1b[0m"]
    assert all(visible_width(line) == 3 for line in lines)


def test_format_tokens_uses_expected_suffixes() -> None:
    assert format_tokens(999) == "999"
    assert format_tokens(1_000) == "1K"
    assert format_tokens(1_500) == "1.5K"
    assert format_tokens(1_000_000) == "1M"
