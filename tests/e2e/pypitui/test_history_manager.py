"""Unit tests for HistoryManager.

All tests use shared fixtures from conftest.py.
"""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.pypitui.conftest import InvariantAssertions

    from alfred.interfaces.pypitui.history_cache import HistoryManager


def test_history_manager_initialization(history_manager: HistoryManager) -> None:
    """Test that HistoryManager initializes with empty history."""
    assert len(history_manager._history) == 0
    assert history_manager._index == 0
    assert history_manager._saved_input == ""


def test_add_increments_history_size(
    history_manager: HistoryManager, assert_invariants: InvariantAssertions
) -> None:
    """Test that add() increases history size by 1."""
    # Pre-condition
    assert len(history_manager._history) == 0

    # Operation
    history_manager.add("test message")

    # Post-condition
    assert len(history_manager._history) == 1
    assert history_manager._history[0].message == "test message"

    # Invariants
    assert_invariants.history_size_bounded(history_manager)


def test_add_empty_message_ignored(history_manager: HistoryManager) -> None:
    """Test that empty or whitespace-only messages are ignored."""
    history_manager.add("")
    history_manager.add("   ")
    history_manager.add("\t\n")

    assert len(history_manager._history) == 0


def test_add_strips_whitespace(history_manager: HistoryManager) -> None:
    """Test that messages are stored with whitespace stripped."""
    history_manager.add("  hello world  ")

    assert history_manager._history[0].message == "hello world"


def test_navigate_up_returns_most_recent(
    populated_history: HistoryManager, assert_invariants: InvariantAssertions
) -> None:
    """Test that navigate_up returns most recent entry first."""
    result = populated_history.navigate_up("")

    assert result == "Third message"
    assert populated_history._index == 1
    assert_invariants.index_valid(populated_history)


def test_navigate_up_saves_current_input(populated_history: HistoryManager) -> None:
    """Test that navigate_up saves current input when moving from position 0."""
    current_input = "unsent message"

    populated_history.navigate_up(current_input)

    assert populated_history._saved_input == current_input


def test_navigate_up_multiple_times(
    populated_history: HistoryManager, assert_invariants: InvariantAssertions
) -> None:
    """Test navigating up through multiple entries."""
    # First up - most recent
    result = populated_history.navigate_up("")
    assert result == "Third message"
    assert populated_history._index == 1

    # Second up
    result = populated_history.navigate_up("")
    assert result == "Second message"
    assert populated_history._index == 2

    # Third up
    result = populated_history.navigate_up("")
    assert result == "First message"
    assert populated_history._index == 3

    # Fourth up - should stay at oldest
    result = populated_history.navigate_up("")
    assert result == "First message"
    assert populated_history._index == 3

    assert_invariants.index_valid(populated_history)


def test_navigate_down_returns_newer(
    populated_history: HistoryManager, assert_invariants: InvariantAssertions
) -> None:
    """Test that navigate_down returns newer entries."""
    # First go up twice
    populated_history.navigate_up("")
    populated_history.navigate_up("")
    assert populated_history._index == 2

    # Now go down
    result = populated_history.navigate_down()
    assert result == "Third message"
    assert populated_history._index == 1

    assert_invariants.index_valid(populated_history)


def test_navigate_down_returns_saved_input(populated_history: HistoryManager) -> None:
    """Test that navigate_down returns to saved input at position 0."""
    saved = "my input"

    # Go up then down
    populated_history.navigate_up(saved)
    result = populated_history.navigate_down()

    assert result == saved
    assert populated_history._index == 0


def test_navigate_down_at_zero_returns_saved_input(history_manager: HistoryManager) -> None:
    """Test navigate_down at index 0 returns saved input."""
    history_manager._saved_input = "saved"

    result = history_manager.navigate_down()

    assert result == "saved"


def test_deduplication_consecutive_duplicates(
    history_with_duplicates: HistoryManager, assert_invariants: InvariantAssertions
) -> None:
    """Test that consecutive duplicate messages are deduplicated."""
    # History should be: ["Duplicate", "Unique", "Duplicate"]
    # The consecutive "Duplicate" at start should be merged
    messages = [entry.message for entry in history_with_duplicates._history]

    assert messages == ["Duplicate", "Unique", "Duplicate"]
    assert len(history_with_duplicates._history) == 3
    assert_invariants.no_consecutive_duplicates(history_with_duplicates)


def test_no_deduplication_non_consecutive(history_manager: HistoryManager) -> None:
    """Test that non-consecutive duplicates are preserved."""
    history_manager.add("A")
    history_manager.add("B")
    history_manager.add("A")

    messages = [entry.message for entry in history_manager._history]
    assert messages == ["A", "B", "A"]


@pytest.mark.slow
def test_eviction_at_max_capacity(
    history_at_max_capacity: HistoryManager, assert_invariants: InvariantAssertions
) -> None:
    """Test that oldest entries are evicted when at capacity."""
    initial_first = history_at_max_capacity._history[0].message

    # Add one more - should evict oldest
    history_at_max_capacity.add("New message")

    # Size should still be at max
    assert len(history_at_max_capacity._history) == 100

    # Oldest should be gone, newest should be added
    assert history_at_max_capacity._history[0].message != initial_first
    assert history_at_max_capacity._history[-1].message == "New message"

    assert_invariants.history_size_bounded(history_at_max_capacity)


def test_clear_history(history_manager: HistoryManager) -> None:
    """Test that clear() removes all history."""
    history_manager.add("A")
    history_manager.add("B")
    history_manager._index = 2
    history_manager._saved_input = "saved"

    history_manager.clear()

    assert len(history_manager._history) == 0
    assert history_manager._index == 0
    assert history_manager._saved_input == ""


def test_size_property(history_manager: HistoryManager) -> None:
    """Test size property returns correct count."""
    assert history_manager.size == 0

    history_manager.add("A")
    assert history_manager.size == 1

    history_manager.add("B")
    assert history_manager.size == 2


def test_is_empty_property(history_manager: HistoryManager) -> None:
    """Test is_empty property."""
    assert history_manager.is_empty is True

    history_manager.add("A")
    assert history_manager.is_empty is False

    history_manager.clear()
    assert history_manager.is_empty is True


def test_navigate_up_empty_history(history_manager: HistoryManager) -> None:
    """Test navigate_up with empty history returns current input."""
    result = history_manager.navigate_up("test")
    assert result == "test"


def test_navigate_down_empty_history(history_manager: HistoryManager) -> None:
    """Test navigate_down with empty history returns saved input."""
    history_manager._saved_input = "saved"
    result = history_manager.navigate_down()
    assert result == "saved"


def test_entry_has_working_dir(history_manager: HistoryManager, temp_work_dir: Path) -> None:
    """Test that entries store the working directory."""
    history_manager.add("test message")

    entry = history_manager._history[0]
    assert entry.working_dir == str(temp_work_dir)


def test_entry_has_timestamp(history_manager: HistoryManager) -> None:
    """Test that entries store a timestamp."""
    from datetime import datetime

    history_manager.add("test message")

    entry = history_manager._history[0]
    assert isinstance(entry.timestamp, datetime)
    # Should be very recent (timezone-aware UTC)
    assert entry.timestamp.tzinfo is not None
    assert (datetime.now(UTC) - entry.timestamp).total_seconds() < 1
