"""Per-directory message history with SQLite persistence.

This module provides history management for the TUI, allowing users
to recall previous messages using Up/Down arrow keys (like bash).
History is scoped to the working directory and persists across sessions.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

# Type aliases for clarity (Python 3.12+ syntax)
type HistoryIndex = int
type CacheHash = str
type MessageText = str


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """Immutable single history entry with timestamp.

    Attributes:
        message: The message text entered by user
        timestamp: UTC datetime when message was added
        working_dir: Absolute path of working directory for debugging
    """

    message: str
    timestamp: datetime
    working_dir: str

    def to_row(self) -> tuple[str, str, str]:
        """Serialize entry to SQLite row tuple."""
        return (self.message, self.timestamp.isoformat(), self.working_dir)

    @classmethod
    def from_row(cls, row: tuple[str, str, str]) -> HistoryEntry:
        """Deserialize entry from SQLite row."""
        return cls(
            message=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            working_dir=row[2],
        )


class HistoryManager:
    """Manages per-directory message history with SQLite cache.

    Thread-safe: SQLite handles concurrent access.

    Attributes:
        _working_dir: The directory this history is scoped to
        _db_path: Path to the SQLite database file
        _max_history: Maximum entries before eviction
        _history: In-memory list of history entries
        _index: Current navigation position (0 = saved input)
        _saved_input: Input text saved when navigating up
    """

    _HASH_LENGTH: Final[int] = 16

    def __init__(
        self,
        working_dir: Path,
        cache_dir: Path,
        max_history: int = 100,
    ) -> None:
        """Initialize HistoryManager.

        Args:
            working_dir: The directory to scope history to
            cache_dir: Directory for SQLite database
            max_history: Maximum number of entries to store (default: 100)
        """
        self._working_dir: Path = working_dir.resolve()
        self._db_path: Path = cache_dir / "history.db"
        self._max_history: int = max_history

        self._history: list[HistoryEntry] = []
        self._index: HistoryIndex = 0
        self._saved_input: MessageText = ""

        # Initialize DB and load cache
        self._init_db()
        self._load_cache()

    def _dir_hash(self, path: Path) -> CacheHash:
        """Generate unique hash for directory path.

        Uses SHA256 truncated to _HASH_LENGTH characters.

        Args:
            path: Directory path to hash

        Returns:
            Truncated SHA256 hash string
        """
        full_hash: str = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()
        return full_hash[: self._HASH_LENGTH]

    def _init_db(self) -> None:
        """Initialize SQLite database with schema if not exists."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with sqlite3.connect(self._db_path) as conn:
                _ = conn.execute("""
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dir_hash TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        working_dir TEXT NOT NULL
                    )
                """)
                _ = conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_dir_hash
                    ON history(dir_hash)
                """)
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"History database init error: {e}")

    def _load_cache(self) -> None:
        """Load history from SQLite for this working directory."""
        dir_hash: str = self._dir_hash(self._working_dir)

        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT message, timestamp, working_dir
                    FROM history
                    WHERE dir_hash = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (dir_hash, self._max_history),
                )
                rows = cursor.fetchall()
                # Reverse to get chronological order
                self._history = [HistoryEntry.from_row(row) for row in reversed(rows)]
        except sqlite3.Error as e:
            logger.warning(f"History database load error: {e}")
            self._history = []

    def _save_cache(self) -> None:
        """Save history to SQLite, replacing existing entries for this directory."""
        dir_hash: str = self._dir_hash(self._working_dir)

        try:
            with sqlite3.connect(self._db_path) as conn:
                # Delete existing entries for this directory
                _ = conn.execute("DELETE FROM history WHERE dir_hash = ?", (dir_hash,))

                # Insert current history
                for entry in self._history:
                    _ = conn.execute(
                        """
                        INSERT INTO history (dir_hash, message, timestamp, working_dir)
                        VALUES (?, ?, ?, ?)
                        """,
                        (dir_hash, *entry.to_row()),
                    )

                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"History database save error: {e}")

    def add(self, message: MessageText) -> None:
        """Add message to history and persist to cache.

        Deduplicates consecutive identical messages.
        Evicts oldest if at capacity.

        Args:
            message: The message text to add
        """
        if not message or not message.strip():
            return

        stripped: str = message.strip()

        # Deduplicate consecutive entries
        if self._history and self._history[-1].message == stripped:
            return

        self._history.append(
            HistoryEntry(
                message=stripped,
                timestamp=datetime.now(UTC),
                working_dir=str(self._working_dir),
            )
        )

        # Evict oldest if over capacity
        if len(self._history) > self._max_history:
            self._history.pop(0)

        self._save_cache()

    def navigate_up(self, current_input: MessageText) -> MessageText:
        """Get previous history item.

        Saves current_input when moving from position 0.
        Returns current input if already at oldest history.

        Args:
            current_input: Current input text to save at position 0

        Returns:
            The previous history message or current_input if at end
        """
        if not self._history:
            return current_input

        if self._index == 0:
            self._saved_input = current_input

        self._index = min(self._index + 1, len(self._history))
        return self._history[-self._index].message

    def navigate_down(self) -> MessageText:
        """Get next history item or return to saved input.

        Returns saved input when index reaches 0.

        Returns:
            The next history message or saved input
        """
        if self._index == 0:
            return self._saved_input

        self._index -= 1

        if self._index == 0:
            return self._saved_input

        return self._history[-self._index].message

    def clear(self) -> None:
        """Clear history and delete database entries for this directory."""
        self._history.clear()
        self._index = 0
        self._saved_input = ""

        dir_hash: str = self._dir_hash(self._working_dir)

        try:
            with sqlite3.connect(self._db_path) as conn:
                _ = conn.execute("DELETE FROM history WHERE dir_hash = ?", (dir_hash,))
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"History database clear error: {e}")

    @property
    def size(self) -> int:
        """Current number of history entries."""
        return len(self._history)

    @property
    def is_empty(self) -> bool:
        """True if no history entries."""
        return len(self._history) == 0

    @property
    def is_navigating(self) -> bool:
        """True if currently navigating history (not at position 0)."""
        return self._index > 0

    def close(self) -> None:
        """Close any resources held by the manager.

        Currently a no-op since SQLite connections are context-managed,
        but provided for future-proofing and explicit cleanup.
        """

    def __enter__(self) -> HistoryManager:
        """Enter context manager."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Exit context manager and cleanup resources."""
        self.close()
