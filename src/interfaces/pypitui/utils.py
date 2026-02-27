"""Utility functions for PyPiTUI components."""


def format_tokens(n: int) -> str:
    """Format token count: 1234567 -> 1.2M, 12345 -> 12K, 123 -> 123."""
    if n >= 1_000_000:
        value = n / 1_000_000
        if value == int(value):
            return f"{int(value)}M"
        return f"{value:.1f}M"
    elif n >= 1_000:
        value = n / 1_000
        if value == int(value):
            return f"{int(value)}K"
        return f"{value:.1f}K"
    return str(n)
