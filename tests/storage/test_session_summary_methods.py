"""Tests for session summary storage methods in SQLiteStore."""

import json
from datetime import UTC, datetime

import aiosqlite
import pytest

from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    """Create temporary SQLiteStore for testing."""
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path)
    await store._init()
    return store


@pytest.fixture
async def sample_summary():
    """Create sample session summary."""
    return {
        "summary_id": "sum_test_001",
        "session_id": "sess_test_001",
        "created_at": datetime(2026, 3, 7, 10, 0, 0, tzinfo=UTC),
        "message_count": 5,
        "first_message_idx": 0,
        "last_message_idx": 4,
        "summary_text": "Test conversation about database design",
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
        "version": 1,
    }


@pytest.fixture
async def db_conn(sqlite_store):
    """Get database connection for testing."""
    async with aiosqlite.connect(sqlite_store.db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


class TestSaveSummary:
    """Tests for save_summary method."""

    @pytest.mark.asyncio
    async def test_save_summary_inserts_new(self, sqlite_store, db_conn, sample_summary):
        """Verify save_summary inserts a new summary."""
        # Insert parent session first
        await db_conn.execute(
            "INSERT INTO sessions (session_id, messages) VALUES (?, ?)",
            (sample_summary["session_id"], "[]"),
        )
        await db_conn.commit()

        # Save summary via store method
        await sqlite_store.save_summary(sample_summary)

        # Verify insert worked
        async with db_conn.execute(
            "SELECT summary_id, summary_text FROM session_summaries WHERE summary_id = ?",
            (sample_summary["summary_id"],),
        ) as cursor:
            row = await cursor.fetchone()
            assert row[0] == sample_summary["summary_id"]
            assert row[1] == sample_summary["summary_text"]

    @pytest.mark.asyncio
    async def test_save_summary_with_embedding(self, sqlite_store, db_conn, sample_summary):
        """Verify embedding is stored as JSON."""
        await db_conn.execute(
            "INSERT INTO sessions (session_id, messages) VALUES (?, ?)",
            (sample_summary["session_id"], "[]"),
        )
        await db_conn.commit()

        await sqlite_store.save_summary(sample_summary)

        # Verify embedding stored as JSON
        async with db_conn.execute(
            "SELECT embedding FROM session_summaries WHERE summary_id = ?",
            (sample_summary["summary_id"],),
        ) as cursor:
            row = await cursor.fetchone()
            stored_embedding = json.loads(row[0])
            assert stored_embedding == sample_summary["embedding"]


class TestGetLatestSummary:
    """Tests for get_latest_summary method."""

    @pytest.mark.asyncio
    async def test_get_latest_summary_returns_most_recent(self, sqlite_store, db_conn):
        """Verify returns summary with highest version."""
        session_id = "sess_version_test"

        # Insert parent session
        await db_conn.execute(
            "INSERT INTO sessions (session_id, messages) VALUES (?, ?)", (session_id, "[]")
        )

        # Insert two summaries for same session
        summaries = [
            {
                "summary_id": "sum_v1",
                "session_id": session_id,
                "message_count": 3,
                "first_message_idx": 0,
                "last_message_idx": 2,
                "summary_text": "First version",
                "version": 1,
            },
            {
                "summary_id": "sum_v2",
                "session_id": session_id,
                "message_count": 5,
                "first_message_idx": 0,
                "last_message_idx": 4,
                "summary_text": "Second version",
                "version": 2,
            },
        ]

        for s in summaries:
            await db_conn.execute(
                """
                INSERT INTO session_summaries (
                    summary_id, session_id, message_count,
                    first_message_idx, last_message_idx, summary_text, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s["summary_id"],
                    s["session_id"],
                    s["message_count"],
                    s["first_message_idx"],
                    s["last_message_idx"],
                    s["summary_text"],
                    s["version"],
                ),
            )
        await db_conn.commit()

        # Get latest - should return version 2
        result = await sqlite_store.get_latest_summary(session_id)

        assert result is not None
        assert result["summary_id"] == "sum_v2"
        assert result["version"] == 2
        assert result["summary_text"] == "Second version"

    @pytest.mark.asyncio
    async def test_get_latest_summary_none_exists(self, sqlite_store):
        """Verify returns None if no summary exists."""
        result = await sqlite_store.get_latest_summary("sess_nonexistent")

        assert result is None


class TestFindSessionsNeedingSummary:
    """Tests for find_sessions_needing_summary method."""

    @pytest.mark.asyncio
    async def test_find_by_message_count(self, sqlite_store, db_conn):
        """Find sessions with 20+ new messages since last summary."""
        # Insert sessions with message counts
        sessions = [
            ("sess_needs_summary", 25, "[]"),  # 25 messages, no summary yet
            ("sess_up_to_date", 15, "[]"),  # 15 messages, no summary
            ("sess_recent_summary", 30, "[]"),  # 30 messages, has summary
        ]

        for session_id, msg_count, messages in sessions:
            await db_conn.execute(
                "INSERT INTO sessions (session_id, message_count, messages) VALUES (?, ?, ?)",
                (session_id, msg_count, messages),
            )

        # Add summary for sess_recent_summary (25 messages at time of summary)
        await db_conn.execute(
            """
            INSERT INTO session_summaries (
                summary_id, session_id, message_count,
                first_message_idx, last_message_idx, summary_text, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("sum_recent", "sess_recent_summary", 25, 0, 24, "Recent summary", 1),
        )
        await db_conn.commit()

        # Find sessions needing summary (threshold = 20)
        result = await sqlite_store.find_sessions_needing_summary(threshold=20)

        # sess_needs_summary: 25 - 0 = 25 >= 20 ✓
        # sess_up_to_date: 15 - 0 = 15 < 20 ✗
        # sess_recent_summary: 30 - 25 = 5 < 20 ✗
        assert "sess_needs_summary" in result
        assert "sess_up_to_date" not in result
        assert "sess_recent_summary" not in result
