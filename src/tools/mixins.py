"""Shared mixins for tool implementations (PRD #109 M6).

Reduces boilerplate by extracting common patterns from tools.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any


class MemoryStoreMixin:
    """Mixin for tools that need memory store access."""

    def __init__(self, memory_store: Any = None) -> None:
        self._memory_store = memory_store

    def set_memory_store(self, memory_store: Any) -> None:
        """Set the memory store after initialization."""
        self._memory_store = memory_store

    def _require_memory_store(self) -> AsyncIterator[str] | None:
        """Check if memory store is available.

        Yields error message if not available, otherwise returns None.
        """
        if not self._memory_store:
            yield "Error: Memory store not initialized"
        return None


class ErrorHandlingMixin:
    """Mixin for consistent error handling in tools."""

    async def _handle_error(self, message: str, exception: Exception | None = None) -> AsyncIterator[str]:
        """Format and yield error message."""
        error_msg = f"{message}: {exception}" if exception else message
        yield error_msg

    def _format_success(self, message: str, details: dict[str, Any] | None = None) -> str:
        """Format success message with optional details."""
        if details:
            detail_str = ", ".join(f"{k}: {v}" for k, v in details.items() if v)
            if detail_str:
                return f"{message} ({detail_str})"
        return message


class SearchResultMixin:
    """Mixin for formatting search results."""

    def _format_entry(self, entry: Any, similarity: float = 0.0, score: float = 0.0) -> str:
        """Format a single memory entry for display."""
        date_str = entry.timestamp.strftime("%Y-%m-%d")
        sim_pct = int(similarity * 100)
        scr_pct = int(score * 100)
        return (
            f"- [{date_str}] {entry.content} "
            f"(sim: {sim_pct}%, score: {scr_pct}%, id: {entry.entry_id})"
        )

    def _format_results(
        self,
        results: list[Any],
        similarities: dict[str, float] | None = None,
        scores: dict[str, float] | None = None,
    ) -> str:
        """Format multiple search results."""
        if not results:
            return "No relevant memories found."

        similarities = similarities or {}
        scores = scores or {}

        lines = []
        for entry in results:
            sim = similarities.get(entry.entry_id, 0.0)
            scr = scores.get(entry.entry_id, 0.0)
            lines.append(self._format_entry(entry, sim, scr))

        return "\n".join(lines)


class TagParsingMixin:
    """Mixin for parsing comma-separated tags."""

    def _parse_tags(self, tags_str: str) -> list[str]:
        """Parse comma-separated tags string into list."""
        return [t.strip() for t in tags_str.split(",") if t.strip()]

    def _format_tags(self, tags: list[str]) -> str:
        """Format tags for display."""
        return f" (tags: {', '.join(tags)})" if tags else ""


class ContentTruncationMixin:
    """Mixin for truncating content."""

    def _truncate(self, content: str, max_len: int = 100, suffix: str = "...") -> str:
        """Truncate content to max length."""
        if len(content) <= max_len:
            return content
        return content[:max_len] + suffix
