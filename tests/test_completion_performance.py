"""Tests for completion performance optimizations.

Tests for:
1. Session metadata caching in SessionStorage
2. Debounced completion updates in CompletionManager
"""

import time
from pathlib import Path

import pytest

from alfred.session import SessionMeta

# === Session Metadata Cache Tests ===


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    """Create temporary sessions directory."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True)
    return sessions_dir


@pytest.fixture
def embedder():
    """Create mock embedder."""

    class MockEmbedder:
        async def embed(self, text: str) -> list[float]:
            return [0.1, 0.2, 0.3]

        async def embed_batch(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2, 0.3] for _ in texts]

    return MockEmbedder()


@pytest.fixture
def storage(sessions_dir: Path, embedder):
    """Create SessionStorage instance with cache support."""
    from alfred.session_storage import SessionStorage

    storage = SessionStorage.__new__(SessionStorage)
    storage.sessions_dir = sessions_dir
    storage.current_path = sessions_dir / "current.json"
    storage.embedder = embedder
    # Initialize cache attributes (will be added in implementation)
    storage._session_cache: dict[str, SessionMeta] | None = None
    storage._cache_timestamp: float = 0
    storage._cache_ttl: float = 5.0
    return storage


class TestSessionMetadataCache:
    """Tests for session metadata caching."""

    def test_list_sessions_cached_returns_sessions(self, storage):
        """list_sessions_cached returns list of SessionMeta objects."""
        # Create test sessions
        storage.create_session("sess_aaa")
        storage.create_session("sess_bbb")

        # Get cached list
        sessions = storage.list_sessions_cached()

        assert len(sessions) == 2
        assert all(isinstance(s, SessionMeta) for s in sessions)
        ids = [s.session_id for s in sessions]
        assert "sess_aaa" in ids
        assert "sess_bbb" in ids

    def test_list_sessions_cached_uses_cache_within_ttl(self, storage):
        """list_sessions_cached returns cached data within TTL without filesystem scan."""
        # Create initial session
        storage.create_session("sess_first")

        # First call populates cache
        first_result = storage.list_sessions_cached()
        assert len(first_result) == 1

        # Create new session (simulates external change)
        storage.create_session("sess_second")

        # Second call within TTL should return cached result (only 1 session)
        second_result = storage.list_sessions_cached()
        assert len(second_result) == 1, "Should return cached result, not scan filesystem"

    def test_list_sessions_cached_refreshes_after_ttl(self, storage):
        """list_sessions_cached refreshes cache after TTL expires."""
        # Set very short TTL for testing
        storage._cache_ttl = 0.01  # 10ms

        # Create initial session
        storage.create_session("sess_first")

        # First call populates cache
        first_result = storage.list_sessions_cached()
        assert len(first_result) == 1

        # Wait for TTL to expire
        time.sleep(0.02)

        # Create new session
        storage.create_session("sess_second")

        # Should refresh from filesystem
        second_result = storage.list_sessions_cached()
        assert len(second_result) == 2, "Should refresh after TTL expires"

    def test_invalidate_session_cache_clears_cache(self, storage):
        """invalidate_session_cache clears cached data."""
        storage.create_session("sess_test")

        # Populate cache
        storage.list_sessions_cached()
        assert storage._session_cache is not None

        # Invalidate
        storage.invalidate_session_cache()
        assert storage._session_cache is None

        # Create new session
        storage.create_session("sess_new")

        # Next call should fetch fresh data
        result = storage.list_sessions_cached()
        assert len(result) == 2

    def test_list_sessions_cached_empty_returns_empty_list(self, storage):
        """list_sessions_cached returns empty list when no sessions exist."""
        result = storage.list_sessions_cached()
        assert result == []

    def test_get_meta_cached_uses_cache(self, storage):
        """get_meta_cached returns metadata from cache if available."""
        storage.create_session("sess_test")

        # Populate cache
        storage.list_sessions_cached()

        # get_meta_cached should return from cache (no file read)
        meta = storage.get_meta_cached("sess_test")
        assert meta is not None
        assert meta.session_id == "sess_test"

    def test_get_meta_cached_returns_none_if_not_in_cache(self, storage):
        """get_meta_cached returns None if session not in cache."""
        # Empty cache
        meta = storage.get_meta_cached("nonexistent")
        assert meta is None


# === Debounced Completion Tests ===


class TestDebouncedCompletion:
    """Tests for debounced completion updates.

    Note: These tests verify the debounce mechanism conceptually.
    Full integration requires running the actual TUI.
    """

    def test_debounce_delay_is_configurable(self):
        """Debounce delay should be configurable on CompletionManager."""
        # Verify the completion_addon module has debounce support
        # by checking the source code contains expected patterns
        import inspect

        from alfred.interfaces.pypitui import completion_addon

        source = inspect.getsource(completion_addon.CompletionManager)

        # Check for debounce-related attributes
        assert "_debounce_delay_ms" in source
        assert "_pending_update_time" in source
        assert "check_pending_update" in source

    def test_debounce_mechanism_exists(self):
        """CompletionManager should have debounce mechanism."""
        from alfred.interfaces.pypitui.completion_addon import CompletionManager

        # Verify the class has the debounce attributes
        assert hasattr(CompletionManager, "_update_completion")
        assert hasattr(CompletionManager, "check_pending_update")



