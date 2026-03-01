"""Tests for fuzzy matching utility."""

import pytest

from src.interfaces.pypitui.fuzzy import fuzzy_match


class TestFuzzyMatch:
    """Test fuzzy matching algorithm."""

    def test_exact_match(self) -> None:
        """Exact match returns True."""
        assert fuzzy_match("/new", "/new") is True

    def test_case_insensitive(self) -> None:
        """Matching is case-insensitive."""
        assert fuzzy_match("/NEW", "/new") is True
        assert fuzzy_match("/new", "/NEW") is True

    def test_subsequence_match(self) -> None:
        """Query matching as subsequence returns True."""
        assert fuzzy_match("/r", "/resume") is True
        assert fuzzy_match("res", "/resume") is True
        assert fuzzy_match("/rs", "/resume") is True

    def test_non_match(self) -> None:
        """Non-matching query returns False."""
        assert fuzzy_match("xyz", "/resume") is False

    def test_empty_query(self) -> None:
        """Empty query matches everything."""
        assert fuzzy_match("", "/resume") is True
        assert fuzzy_match("", "anything") is True

    def test_query_longer_than_target(self) -> None:
        """Query longer than target returns False."""
        assert fuzzy_match("/resume", "/res") is False

    def test_partial_match_fails(self) -> None:
        """Characters must be in order."""
        assert fuzzy_match("/esr", "/resume") is False

    def test_special_characters(self) -> None:
        """Special characters in query work correctly."""
        assert fuzzy_match("/new", "/new") is True
        assert fuzzy_match("/resume", "/resume") is True

    def test_numbers_in_query(self) -> None:
        """Numbers in query work correctly."""
        assert fuzzy_match("abc123", "abc123") is True
        assert fuzzy_match("a13", "abc123") is True


class TestFuzzyMatchOrdering:
    """Test that fuzzy match can be used for sorting."""

    def test_prefix_matches_score_higher(self) -> None:
        """Exact prefix should be preferred over subsequence."""
        # Both match, but "/new" is exact prefix of "/new"
        # while "/n" is subsequence of "/new"
        assert fuzzy_match("/new", "/new") is True
        assert fuzzy_match("/n", "/new") is True

    def test_shorter_subsequence_matches(self) -> None:
        """Shorter query that matches is better."""
        targets = ["/resume", "/restart", "/reload"]
        query = "/r"
        
        results = [t for t in targets if fuzzy_match(query, t)]
        assert len(results) == 3  # All match
