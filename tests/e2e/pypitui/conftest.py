"""Shared fixtures for pypitui tests.

All test dependencies come from fixtures. Zero inline setup.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from pypitui import MockTerminal

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.history_cache import HistoryEntry, HistoryManager

# Type aliases for fixture return types (Python 3.12+ syntax)
type ConfigDict = dict[str, int | str]
type CacheEntryFactory = Callable[[str, int], "HistoryEntry"]


@pytest.fixture(scope="session")
def default_config() -> ConfigDict:
    """Default configuration for all history tests.

    Returns:
        Dictionary with max_history setting
    """
    return {"max_history": 100}


@pytest.fixture
def temp_cache_dir() -> Iterator[Path]:
    """Temporary cache directory for isolated tests.

    Yields:
        Path to temporary cache directory
    """
    with tempfile.TemporaryDirectory() as tmp:
        cache_path = Path(tmp) / "cache"
        cache_path.mkdir(parents=True, exist_ok=True)
        yield cache_path


@pytest.fixture
def temp_work_dir() -> Iterator[Path]:
    """Temporary working directory simulating project directory.

    Yields:
        Path to temporary working directory
    """
    with tempfile.TemporaryDirectory() as tmp:
        work_path = Path(tmp) / "project"
        work_path.mkdir(parents=True, exist_ok=True)
        yield work_path


@pytest.fixture
def history_manager(temp_work_dir: Path, temp_cache_dir: Path, default_config: ConfigDict) -> HistoryManager:
    """HistoryManager with default configuration.

    Returns:
        Configured HistoryManager instance
    """
    from alfred.interfaces.pypitui.history_cache import HistoryManager

    return HistoryManager(
        working_dir=temp_work_dir,
        cache_dir=temp_cache_dir,
        max_history=int(default_config["max_history"]),
    )


@pytest.fixture
def populated_history(history_manager: HistoryManager) -> HistoryManager:
    """HistoryManager with 3 entries for navigation testing.

    Returns:
        HistoryManager with 3 added entries
    """
    history_manager.add("First message")
    history_manager.add("Second message")
    history_manager.add("Third message")
    return history_manager


@pytest.fixture
def history_at_max_capacity(history_manager: HistoryManager, default_config: ConfigDict) -> HistoryManager:
    """HistoryManager at max_history limit.

    Returns:
        HistoryManager filled to capacity
    """
    max_history = int(default_config["max_history"])
    for i in range(max_history):
        history_manager.add(f"Message {i}")
    return history_manager


@pytest.fixture
def history_with_duplicates(history_manager: HistoryManager) -> HistoryManager:
    """HistoryManager with consecutive duplicates.

    Returns:
        HistoryManager with duplicate entries
    """
    history_manager.add("Duplicate")
    history_manager.add("Duplicate")  # Should be deduplicated
    history_manager.add("Unique")
    history_manager.add("Duplicate")  # Not consecutive, should remain
    return history_manager


@pytest.fixture
def aged_cache_entry() -> CacheEntryFactory:
    """Factory for creating cache entries with specific age.

    Returns:
        Factory function: (message: str, days_ago: int) -> HistoryEntry
    """

    def _create(message: str, days_ago: int) -> HistoryEntry:
        from alfred.interfaces.pypitui.history_cache import HistoryEntry

        return HistoryEntry(
            message=message,
            timestamp=datetime.now() - timedelta(days=days_ago),
            working_dir="/test",
        )

    return _create


@pytest.fixture
def corrupted_cache_file(temp_cache_dir: Path) -> Path:
    """Cache file with invalid content.

    Returns:
        Path to corrupted cache file
    """
    db_path = temp_cache_dir / "history.db"
    db_path.write_text("not a valid sqlite database")
    return db_path


@pytest.fixture
def readonly_cache_dir(temp_cache_dir: Path) -> Path:
    """Cache directory without write permissions.

    Returns:
        Path to read-only cache directory
    """
    temp_cache_dir.chmod(0o555)  # read-only
    return temp_cache_dir


class InvariantAssertions:
    """Helper class for invariant assertions."""

    @staticmethod
    def history_size_bounded(history: HistoryManager, max_size: int = 100) -> None:
        """History never exceeds max_history."""
        msg = f"History size {len(history._history)} exceeds max {max_size}"
        assert len(history._history) <= max_size, msg

    @staticmethod
    def no_consecutive_duplicates(history: HistoryManager) -> None:
        """No two consecutive entries are identical."""
        for i in range(len(history._history) - 1):
            assert history._history[i].message != history._history[i + 1].message, f"Duplicate messages at indices {i} and {i + 1}"

    @staticmethod
    def index_valid(history: HistoryManager) -> None:
        """Navigation index always in valid range."""
        assert 0 <= history._index <= len(history._history), f"Index {history._index} out of range [0, {len(history._history)}]"


@pytest.fixture
def assert_invariants() -> InvariantAssertions:
    """Fixture providing invariant assertion helpers.

    Returns:
        InvariantAssertions instance
    """
    return InvariantAssertions()


@pytest.fixture
def mock_alfred() -> MagicMock:
    """Mock Alfred instance for TUI tests.

    Returns:
        Mocked Alfred instance with token_tracker and config
    """
    mock = MagicMock()
    mock.token_tracker.usage.input_tokens = 100
    mock.token_tracker.usage.output_tokens = 50
    mock.token_tracker.usage.cache_read_tokens = 25
    mock.token_tracker.usage.reasoning_tokens = 10
    mock.token_tracker.context_tokens = 200
    mock.model_name = "test-model"
    mock.config.use_markdown_rendering = True
    mock.config.data_dir = Path("/tmp/test")

    # Mock async chat_stream for _send_message tests
    async def mock_chat_stream(*args, **kwargs):
        """Yield a simple response."""
        yield "Hello"
        yield " "
        yield "world!"

    mock.chat_stream = mock_chat_stream
    return mock


@pytest.fixture
def mock_terminal() -> MockTerminal:
    """Mock terminal for TUI tests.

    Returns:
        MockTerminal instance with 80x24 dimensions
    """
    return MockTerminal(cols=80, rows=24)
