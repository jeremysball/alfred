"""Tests for message_embeddings table with sqlite-vec."""

import json
import sqlite3

import aiosqlite
import pytest

from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    """Create temporary SQLiteStore for testing."""
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path, embedding_dim=3)
    await store._init()
    return store


@pytest.fixture
async def db_conn(sqlite_store):
    """Get database connection for testing."""
    async with aiosqlite.connect(sqlite_store.db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


class TestMessageEmbeddingsTable:
    """Tests for message_embeddings table creation."""

    @pytest.mark.asyncio
    async def test_message_embeddings_table_exists(self, sqlite_store, db_conn):
        """Verify message_embeddings table exists."""
        db = db_conn

        # Insert parent session first
        await db.execute(
            "INSERT INTO sessions (session_id, message_count) VALUES (?, ?)",
            ("sess_test", 2),
        )
        await db.execute(
            """
            INSERT INTO session_messages (session_id, message_id, message_idx, role, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("sess_test", "msg-0", 0, "user", json.dumps({"role": "user", "content": "Hello"})),
        )
        await db.commit()

        # Insert message embedding
        await db.execute(
            """
            INSERT INTO message_embeddings
            (message_embedding_id, session_id, message_id, message_idx, role, content_snippet, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("me_test", "sess_test", "msg-0", 0, "user", "Hello", json.dumps([0.1, 0.2, 0.3])),
        )
        await db.commit()

        # Verify
        async with db.execute("SELECT COUNT(*) FROM message_embeddings WHERE message_embedding_id = ?", ("me_test",)) as cursor:
            row = await cursor.fetchone()
            assert row[0] == 1

    @pytest.mark.asyncio
    async def test_message_embeddings_foreign_key(self, sqlite_store, db_conn):
        """Verify FK constraint prevents orphaned embeddings."""
        db = db_conn

        # Try to insert without parent session - should fail
        with pytest.raises(sqlite3.IntegrityError):
            await db.execute(
                """
                INSERT INTO message_embeddings
                (message_embedding_id, session_id, message_id, message_idx, role, content_snippet, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("me_orphan", "nonexistent", "msg-0", 0, "user", "Test", json.dumps([0.1])),
            )
            await db.commit()

    @pytest.mark.asyncio
    async def test_cascade_delete(self, sqlite_store, db_conn):
        """Verify deleting session cascades to message_embeddings."""
        db = db_conn

        # Insert session and message
        await db.execute(
            "INSERT INTO sessions (session_id, message_count) VALUES (?, ?)",
            ("sess_cascade", 1),
        )
        await db.execute(
            """
            INSERT INTO session_messages (session_id, message_id, message_idx, role, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("sess_cascade", "msg-0", 0, "user", json.dumps({"role": "user", "content": "Hi"})),
        )
        await db.execute(
            """
            INSERT INTO message_embeddings
            (message_embedding_id, session_id, message_id, message_idx, role, content_snippet, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("me_cascade", "sess_cascade", "msg-0", 0, "user", "Hi", json.dumps([0.1])),
        )
        await db.commit()

        # Delete session
        await db.execute("DELETE FROM sessions WHERE session_id = ?", ("sess_cascade",))
        await db.commit()

        # Verify message embedding deleted
        async with db.execute("SELECT COUNT(*) FROM message_embeddings WHERE session_id = ?", ("sess_cascade",)) as cursor:
            row = await cursor.fetchone()
            assert row[0] == 0


class TestMessageEmbeddingsIndexing:
    """Tests for automatic indexing on save_session."""

    @pytest.mark.asyncio
    async def test_save_session_indexes_embeddings(self, sqlite_store):
        """Verify save_session() also inserts into message_embeddings."""
        messages = [
            {
                "idx": 0,
                "role": "user",
                "content": "Hello Alfred",
                "embedding": [0.1, 0.2, 0.3],
                "timestamp": "2026-03-07T10:00:00Z",
            },
            {
                "idx": 1,
                "role": "assistant",
                "content": "Hello! How can I help?",
                "embedding": [0.4, 0.5, 0.6],
                "timestamp": "2026-03-07T10:01:00Z",
            },
        ]

        await sqlite_store.save_session("sess_index", messages)

        # Verify message_embeddings created
        import aiosqlite

        async with (
            aiosqlite.connect(sqlite_store.db_path) as db,
            db.execute("SELECT COUNT(*) FROM message_embeddings WHERE session_id = ?", ("sess_index",)) as cursor,
        ):
            row = await cursor.fetchone()
            assert row[0] == 2

    @pytest.mark.asyncio
    async def test_save_session_skips_messages_without_embeddings(self, sqlite_store):
        """Verify messages without embeddings are not indexed."""
        messages = [
            {
                "idx": 0,
                "role": "user",
                "content": "No embedding",
                # No embedding field
            },
            {
                "idx": 1,
                "role": "assistant",
                "content": "Has embedding",
                "embedding": [0.1, 0.2, 0.3],
            },
        ]

        await sqlite_store.save_session("sess_partial", messages)

        # Only 1 message should be indexed
        import aiosqlite

        async with (
            aiosqlite.connect(sqlite_store.db_path) as db,
            db.execute("SELECT COUNT(*) FROM message_embeddings WHERE session_id = ?", ("sess_partial",)) as cursor,
        ):
            row = await cursor.fetchone()
            assert row[0] == 1

    @pytest.mark.asyncio
    async def test_save_session_rebuilds_message_embeddings_with_canonical_message_ids(self, sqlite_store):
        """Verify save_session() rebuilds embeddings against canonical transcript message IDs."""
        initial_messages = [
            {
                "idx": 0,
                "id": "msg-0",
                "role": "user",
                "content": "Hello original",
                "embedding": [0.1, 0.2, 0.3],
            },
            {
                "idx": 1,
                "id": "msg-1",
                "role": "assistant",
                "content": "Initial answer",
                "embedding": [0.4, 0.5, 0.6],
            },
            {
                "idx": 2,
                "id": "msg-2",
                "role": "assistant",
                "content": "Stale tail",
                "embedding": [0.7, 0.8, 0.9],
            },
        ]

        await sqlite_store.save_session("sess_update", initial_messages)

        updated_messages = [
            {
                "idx": 0,
                "id": "msg-0",
                "role": "user",
                "content": "Hello edited",
                "embedding": [0.9, 0.8, 0.7],
            },
            {
                "idx": 1,
                "id": "msg-1",
                "role": "assistant",
                "content": "Rewritten answer",
                "embedding": [0.6, 0.5, 0.4],
            },
        ]

        await sqlite_store.save_session("sess_update", updated_messages)

        import aiosqlite

        async with aiosqlite.connect(sqlite_store.db_path) as db:
            await sqlite_store._load_extensions(db)
            db.row_factory = aiosqlite.Row

            async with db.execute("PRAGMA table_info(message_embeddings)") as cursor:
                embedding_columns = {row["name"] for row in await cursor.fetchall()}

            async with db.execute(
                """
                SELECT message_embedding_id, session_id, message_id, message_idx, content_snippet
                FROM message_embeddings
                WHERE session_id = ?
                ORDER BY message_idx
                """,
                ("sess_update",),
            ) as cursor:
                message_rows = await cursor.fetchall()

            async with db.execute(
                "SELECT message_embedding_id FROM message_embeddings_vec ORDER BY message_embedding_id"
            ) as cursor:
                vec_rows = await cursor.fetchall()

        assert "message_id" in embedding_columns
        assert [
            (
                row["message_embedding_id"],
                row["session_id"],
                row["message_id"],
                row["message_idx"],
                row["content_snippet"],
            )
            for row in message_rows
        ] == [
            ("sess_update:msg-0", "sess_update", "msg-0", 0, "Hello edited"),
            ("sess_update:msg-1", "sess_update", "msg-1", 1, "Rewritten answer"),
        ]
        assert [row["message_embedding_id"] for row in vec_rows] == ["sess_update:msg-0", "sess_update:msg-1"]
