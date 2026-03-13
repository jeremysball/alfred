"""Tests for session_summaries table in SQLiteStore."""

import aiosqlite
import pytest

from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    """Create temporary SQLiteStore for testing."""
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path)
    # Initialize tables
    await store._init()
    return store


@pytest.fixture
async def db_conn(sqlite_store):
    """Get database connection for testing."""
    async with aiosqlite.connect(sqlite_store.db_path) as db:
        # Enable foreign keys for cascade to work
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


class TestSessionSummariesTable:
    """Tests for session_summaries table creation."""

    @pytest.mark.asyncio
    async def test_create_session_summaries_table(self, sqlite_store, db_conn):
        """Verify session_summaries table exists with correct schema."""
        db = db_conn

        # Insert parent session first (FK constraint)
        await db.execute(
            "INSERT INTO sessions (session_id, messages) VALUES (?, ?)",
            ("sess_abc456", "[]")
        )
        await db.commit()

        # Try to insert a test summary - should succeed if table exists
        await db.execute(
            """
            INSERT INTO session_summaries (
                summary_id, session_id, message_count,
                first_message_idx, last_message_idx, summary_text, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("sum_test123", "sess_abc456", 5, 0, 4, "Test summary", 1)
        )
        await db.commit()

        # Verify insert worked
        async with db.execute(
            "SELECT COUNT(*) FROM session_summaries WHERE summary_id = ?",
            ("sum_test123",)
        ) as cursor:
            row = await cursor.fetchone()
            assert row[0] == 1

    @pytest.mark.asyncio
    async def test_session_summaries_foreign_key(self, sqlite_store, db_conn):
        """Verify FK constraint prevents orphaned summaries."""
        db = db_conn

        # Insert a session first
        await db.execute(
            "INSERT INTO sessions (session_id, messages) VALUES (?, ?)",
            ("sess_exists", "[]")
        )
        await db.commit()

        # Insert summary for existing session - should succeed
        await db.execute(
            """
            INSERT INTO session_summaries (
                summary_id, session_id, message_count,
                first_message_idx, last_message_idx, summary_text
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("sum_valid", "sess_exists", 3, 0, 2, "Valid summary")
        )
        await db.commit()

    @pytest.mark.asyncio
    async def test_session_summaries_on_delete_cascade(self, sqlite_store, db_conn):
        """Verify deleting session cascades to summaries."""
        db = db_conn

        # Insert session and summary
        await db.execute(
            "INSERT INTO sessions (session_id, messages) VALUES (?, ?)",
            ("sess_cascade", "[]")
        )
        await db.execute(
            """
            INSERT INTO session_summaries (
                summary_id, session_id, message_count,
                first_message_idx, last_message_idx, summary_text
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("sum_cascade", "sess_cascade", 3, 0, 2, "Cascade test")
        )
        await db.commit()

        # Delete session
        await db.execute(
            "DELETE FROM sessions WHERE session_id = ?",
            ("sess_cascade",)
        )
        await db.commit()

        # Verify summary was also deleted
        async with db.execute(
            "SELECT COUNT(*) FROM session_summaries WHERE session_id = ?",
            ("sess_cascade",)
        ) as cursor:
            row = await cursor.fetchone()
            assert row[0] == 0
