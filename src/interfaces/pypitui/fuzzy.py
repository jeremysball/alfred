"""Fuzzy matching utilities for command completion."""


def fuzzy_match(query: str, target: str) -> bool:
    """Check if query matches target as subsequence (case-insensitive).

    Args:
        query: The search query.
        target: The string to match against.

    Returns:
        True if query matches target as a subsequence.

    Examples:
        >>> fuzzy_match("/r", "/resume")
        True
        >>> fuzzy_match("res", "/resume")
        True
        >>> fuzzy_match("/rs", "/resume")
        True
        >>> fuzzy_match("xyz", "/resume")
        False
    """
    query_lower = query.lower()
    target_lower = target.lower()

    qi = 0
    for char in target_lower:
        if qi < len(query_lower) and char == query_lower[qi]:
            qi += 1

    return qi == len(query_lower)
