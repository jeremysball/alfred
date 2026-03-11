"""Test /new command performance fixes.

This module verifies that the /new command is fast by ensuring:
1. Async methods work properly without run_async overhead
2. Creating a new session completes in reasonable time

Related issues fixed:
- run_async from async context caused deadlocks/timeout
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from alfred.session import SessionManager
from alfred.storage.sqlite import SQLiteStore


class TestNewSessionPerformance:
    """Test that new_session() works correctly with async methods."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Provide a temporary database path."""
        return tmp_path / "test.db"

    async def test_new_session_async(self, temp_db_path: Path) -> None:
        """Test that new_session_async works without run_async overhead."""
        store = SQLiteStore(temp_db_path)

        # Pre-initialize the DB
        await store._init()

        # Create SessionManager via constructor with mock data_dir
        data_dir = temp_db_path.parent
        manager = SessionManager(store=store, data_dir=data_dir)

        # Create a new session using async method
        start = time.perf_counter()
        session = await manager.new_session_async()
        elapsed = time.perf_counter() - start

        # Should complete in under 100ms
        assert elapsed < 0.1, f"new_session_async() took {elapsed:.3f}s, expected < 0.1s"
        assert session is not None
        assert session.meta.session_id is not None

    async def test_resume_session_async(self, temp_db_path: Path) -> None:
        """Test that resume_session_async works without run_async overhead."""
        store = SQLiteStore(temp_db_path)

        # Pre-initialize the DB
        await store._init()

        # Create SessionManager via constructor
        data_dir = temp_db_path.parent
        manager = SessionManager(store=store, data_dir=data_dir)

        # Create a session first (add a message so it's persisted)
        original = await manager.new_session_async()
        manager.add_message("user", "test message")
        original_id = original.meta.session_id

        # Wait for persist
        await asyncio.sleep(0.1)

        # Clear current session
        manager.clear_session()

        # Resume the session using async method
        start = time.perf_counter()
        resumed = await manager.resume_session_async(original_id)
        elapsed = time.perf_counter() - start

        # Should complete in under 100ms
        assert elapsed < 0.1, f"resume_session_async() took {elapsed:.3f}s, expected < 0.1s"
        assert resumed.meta.session_id == original_id

    def test_sync_methods_still_work(self, temp_db_path: Path) -> None:
        """Test that sync methods still work for non-async contexts."""
        store = SQLiteStore(temp_db_path)

        # Create SessionManager via constructor
        data_dir = temp_db_path.parent
        manager = SessionManager(store=store, data_dir=data_dir)

        # Create a new session using sync method (from sync context)
        start = time.perf_counter()
        session = manager.new_session()
        elapsed = time.perf_counter() - start

        # Should complete in reasonable time (< 1s due to DB init)
        assert elapsed < 1.0, f"new_session() took {elapsed:.3f}s, expected < 1.0s"
        assert session is not None
        assert session.meta.session_id is not None
