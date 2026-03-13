"""Tests for history cache persistence.

All tests use shared fixtures from conftest.py.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.history_cache import HistoryManager


def test_cache_creates_database_on_init(temp_cache_dir: Path, temp_work_dir: Path) -> None:
    """Test that HistoryManager creates SQLite database on init."""
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    db_path = temp_cache_dir / "history.db"
    assert not db_path.exists()

    HistoryManager(temp_work_dir, temp_cache_dir)

    assert db_path.exists()


def test_cache_creates_table_schema(temp_cache_dir: Path, temp_work_dir: Path) -> None:
    """Test that database has correct schema."""
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    HistoryManager(temp_work_dir, temp_cache_dir)

    db_path = temp_cache_dir / "history.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='history'"
        )
        assert cursor.fetchone() is not None


def test_cache_saves_on_add(history_manager: HistoryManager, temp_cache_dir: Path) -> None:
    """Test that add() persists to SQLite."""
    history_manager.add("test message")

    # Create new manager - should load from cache
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    new_manager = HistoryManager(history_manager._working_dir, temp_cache_dir)

    assert len(new_manager._history) == 1
    assert new_manager._history[0].message == "test message"


def test_cache_isolated_by_directory(
    temp_cache_dir: Path, temp_work_dir: Path
) -> None:
    """Test that different directories have isolated history."""
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    # Create two different work directories
    work_dir1 = temp_work_dir / "project1"
    work_dir2 = temp_work_dir / "project2"
    work_dir1.mkdir()
    work_dir2.mkdir()

    # Add history to each
    manager1 = HistoryManager(work_dir1, temp_cache_dir)
    manager1.add("project1 message")

    manager2 = HistoryManager(work_dir2, temp_cache_dir)
    manager2.add("project2 message")

    # Reload and verify isolation
    new_manager1 = HistoryManager(work_dir1, temp_cache_dir)
    new_manager2 = HistoryManager(work_dir2, temp_cache_dir)

    assert len(new_manager1._history) == 1
    assert new_manager1._history[0].message == "project1 message"

    assert len(new_manager2._history) == 1
    assert new_manager2._history[0].message == "project2 message"


def test_cache_loads_in_order(temp_cache_dir: Path, temp_work_dir: Path) -> None:
    """Test that cache loads entries in chronological order."""
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    # Create and populate
    manager = HistoryManager(temp_work_dir, temp_cache_dir)
    manager.add("First")
    manager.add("Second")
    manager.add("Third")

    # Reload
    new_manager = HistoryManager(temp_work_dir, temp_cache_dir)

    messages = [entry.message for entry in new_manager._history]
    assert messages == ["First", "Second", "Third"]


def test_cache_clear_deletes_from_database(
    history_manager: HistoryManager, temp_cache_dir: Path
) -> None:
    """Test that clear() removes entries from SQLite."""
    history_manager.add("message to clear")

    # Clear
    history_manager.clear()

    # Reload - should be empty
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    new_manager = HistoryManager(history_manager._working_dir, temp_cache_dir)
    assert len(new_manager._history) == 0


def test_cache_handles_corrupted_database(
    corrupted_cache_file: Path, temp_work_dir: Path
) -> None:
    """Test graceful handling of corrupted database."""
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    cache_dir = corrupted_cache_file.parent

    # Should not crash, just start fresh
    manager = HistoryManager(temp_work_dir, cache_dir)

    assert len(manager._history) == 0

    # Should be able to add entries
    manager.add("new message")
    assert len(manager._history) == 1


def test_cache_handles_readonly_directory(
    readonly_cache_dir: Path, temp_work_dir: Path
) -> None:
    """Test graceful handling of read-only cache directory."""
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    # Should not crash on init
    manager = HistoryManager(temp_work_dir, readonly_cache_dir)

    # Can add to memory
    manager.add("message")
    assert len(manager._history) == 1

    # But won't persist (no error raised, graceful degradation)
    # We can't easily test the non-persistence without re-loading,
    # but at least it doesn't crash


def test_cache_replace_on_write(
    populated_history: HistoryManager, temp_cache_dir: Path
) -> None:
    """Test that save replaces existing entries for directory."""
    # Add more entries after initial population
    populated_history.add("Fourth")

    # Reload
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    new_manager = HistoryManager(populated_history._working_dir, temp_cache_dir)

    # Should have all 4 entries, not duplicates
    assert len(new_manager._history) == 4
    messages = [entry.message for entry in new_manager._history]
    assert messages == ["First message", "Second message", "Third message", "Fourth"]


def test_cache_max_entries_per_directory(
    temp_cache_dir: Path, temp_work_dir: Path
) -> None:
    """Test that max_history applies per directory, not globally."""
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    work_dir1 = temp_work_dir / "project1"
    work_dir2 = temp_work_dir / "project2"
    work_dir1.mkdir()
    work_dir2.mkdir()

    # Add 50 entries to each
    manager1 = HistoryManager(work_dir1, temp_cache_dir, max_history=50)
    manager2 = HistoryManager(work_dir2, temp_cache_dir, max_history=50)

    for i in range(50):
        manager1.add(f"dir1-message-{i}")
        manager2.add(f"dir2-message-{i}")

    # Reload both
    new_manager1 = HistoryManager(work_dir1, temp_cache_dir, max_history=50)
    new_manager2 = HistoryManager(work_dir2, temp_cache_dir, max_history=50)

    # Each should have 50 entries
    assert len(new_manager1._history) == 50
    assert len(new_manager2._history) == 50


def test_cache_includes_working_dir_for_debugging(
    history_manager: HistoryManager, temp_cache_dir: Path
) -> None:
    """Test that cache stores working_dir for debugging."""
    history_manager.add("test")

    db_path = temp_cache_dir / "history.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT working_dir FROM history LIMIT 1")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == str(history_manager._working_dir)


def test_dir_hash_deterministic(
    history_manager: HistoryManager, temp_work_dir: Path
) -> None:
    """Test that directory hash is deterministic."""
    hash1 = history_manager._dir_hash(temp_work_dir)
    hash2 = history_manager._dir_hash(temp_work_dir)

    assert hash1 == hash2
    assert len(hash1) == 16  # Truncated SHA256


def test_dir_hash_different_for_different_paths(
    history_manager: HistoryManager, temp_work_dir: Path
) -> None:
    """Test that different paths produce different hashes."""
    path1 = temp_work_dir / "a"
    path2 = temp_work_dir / "b"
    path1.mkdir()
    path2.mkdir()

    hash1 = history_manager._dir_hash(path1)
    hash2 = history_manager._dir_hash(path2)

    assert hash1 != hash2
