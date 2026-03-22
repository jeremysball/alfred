"""Behavior tests for Alfred-facing similarity semantics in SQLiteStore.

These tests codify the contract that search results must expose higher-is-better
similarity values, not raw backend distance values mislabeled as similarity.
"""

from datetime import UTC, datetime

import aiosqlite
import pytest

from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    """Create a temporary SQLiteStore with a small embedding dimension."""
    store = SQLiteStore(tmp_path / "similarity.db", embedding_dim=3)
    await store._init()
    return store


@pytest.fixture
async def db_conn(sqlite_store):
    """Open a direct database connection for seeding search fixtures."""
    async with aiosqlite.connect(sqlite_store.db_path) as db:
        await sqlite_store._load_extensions(db)
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


class TestMemorySimilaritySemantics:
    """Memory search must expose higher-is-better similarity values."""

    @pytest.mark.asyncio
    async def test_search_memories_returns_higher_is_better_similarity_contract(
        self, sqlite_store, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The closest memory must have the highest returned similarity value."""
        async with aiosqlite.connect(sqlite_store.db_path) as db:
            await sqlite_store._load_extensions(db)
            await db.execute(
                """
                INSERT INTO memories (entry_id, timestamp, role, content, tags, permanent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "mem-close",
                    datetime(2026, 3, 21, tzinfo=UTC),
                    "system",
                    "close memory",
                    "[]",
                    False,
                ),
            )
            await db.execute(
                """
                INSERT INTO memories (entry_id, timestamp, role, content, tags, permanent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "mem-far",
                    datetime(2026, 3, 21, tzinfo=UTC),
                    "system",
                    "far memory",
                    "[]",
                    False,
                ),
            )
            await db.execute(
                "INSERT INTO memory_embeddings (entry_id, embedding) VALUES (?, ?)",
                ("mem-close", "[1.0, 0.0, 0.0]"),
            )
            await db.execute(
                "INSERT INTO memory_embeddings (entry_id, embedding) VALUES (?, ?)",
                ("mem-far", "[0.0, 1.0, 0.0]"),
            )
            await db.commit()

        with caplog.at_level("DEBUG", logger="alfred.storage.sqlite"):
            results = await sqlite_store.search_memories([1.0, 0.0, 0.0], top_k=2)

        assert [row["entry_id"] for row in results] == ["mem-close", "mem-far"]
        assert results[0]["similarity"] > results[1]["similarity"], (
            "Memory search must return higher-is-better similarity, not raw distance"
        )

        storage_messages = [record.message for record in caplog.records if record.name == "alfred.storage.sqlite"]
        assert any(message.startswith("event=storage.memory_search.start") for message in storage_messages)
        assert any(message.startswith("event=storage.memory_search.completed") for message in storage_messages)
        assert any("result_count=2" in message for message in storage_messages)
        assert any("duration_ms=" in message for message in storage_messages)


class TestSessionSimilaritySemantics:
    """Session search must expose higher-is-better similarity values."""

    @pytest.mark.asyncio
    async def test_search_summaries_returns_higher_is_better_similarity_contract(
        self, sqlite_store, db_conn, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The closest session summary must have the highest returned similarity."""
        await db_conn.execute(
            "INSERT INTO sessions (session_id, messages) VALUES (?, ?)",
            ("sess-close", "[]"),
        )
        await db_conn.execute(
            "INSERT INTO sessions (session_id, messages) VALUES (?, ?)",
            ("sess-far", "[]"),
        )
        await db_conn.execute(
            """
            INSERT INTO session_summaries (
                summary_id, session_id, message_count,
                first_message_idx, last_message_idx, summary_text, embedding, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "sum-close",
                "sess-close",
                5,
                0,
                4,
                "close summary",
                "[1.0, 0.0, 0.0]",
                1,
            ),
        )
        await db_conn.execute(
            """
            INSERT INTO session_summaries (
                summary_id, session_id, message_count,
                first_message_idx, last_message_idx, summary_text, embedding, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "sum-far",
                "sess-far",
                5,
                0,
                4,
                "far summary",
                "[0.0, 1.0, 0.0]",
                1,
            ),
        )
        await db_conn.execute(
            "INSERT INTO session_summaries_vec (summary_id, embedding) VALUES (?, ?)",
            ("sum-close", "[1.0, 0.0, 0.0]"),
        )
        await db_conn.execute(
            "INSERT INTO session_summaries_vec (summary_id, embedding) VALUES (?, ?)",
            ("sum-far", "[0.0, 1.0, 0.0]"),
        )
        await db_conn.commit()

        with caplog.at_level("DEBUG", logger="alfred.storage.sqlite"):
            results = await sqlite_store.search_summaries([1.0, 0.0, 0.0], top_k=2)

        assert [row["summary_id"] for row in results] == ["sum-close", "sum-far"]
        assert results[0]["similarity"] > results[1]["similarity"], (
            "Summary search must return higher-is-better similarity, not raw distance"
        )

        storage_messages = [record.message for record in caplog.records if record.name == "alfred.storage.sqlite"]
        assert any(message.startswith("event=storage.session_summary_search.start") for message in storage_messages)
        assert any(message.startswith("event=storage.session_summary_search.completed") for message in storage_messages)
        assert any("result_count=2" in message for message in storage_messages)
        assert any("duration_ms=" in message for message in storage_messages)

    @pytest.mark.asyncio
    async def test_search_session_messages_returns_higher_is_better_similarity_contract(
        self, sqlite_store, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The closest message must have the highest returned similarity."""
        async with aiosqlite.connect(sqlite_store.db_path) as db:
            await sqlite_store._load_extensions(db)
            await db.execute(
                "INSERT INTO sessions (session_id, messages) VALUES (?, ?)",
                ("sess-msg", "[]"),
            )
            await db.execute(
                """
                INSERT INTO message_embeddings (
                    message_embedding_id, session_id, message_idx,
                    role, content_snippet, embedding
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "sess-msg_0",
                    "sess-msg",
                    0,
                    "user",
                    "close message",
                    "[1.0, 0.0, 0.0]",
                ),
            )
            await db.execute(
                """
                INSERT INTO message_embeddings (
                    message_embedding_id, session_id, message_idx,
                    role, content_snippet, embedding
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "sess-msg_1",
                    "sess-msg",
                    1,
                    "assistant",
                    "far message",
                    "[0.0, 1.0, 0.0]",
                ),
            )
            await db.execute(
                "INSERT INTO message_embeddings_vec (message_embedding_id, embedding) VALUES (?, ?)",
                ("sess-msg_0", "[1.0, 0.0, 0.0]"),
            )
            await db.execute(
                "INSERT INTO message_embeddings_vec (message_embedding_id, embedding) VALUES (?, ?)",
                ("sess-msg_1", "[0.0, 1.0, 0.0]"),
            )
            await db.commit()

        with caplog.at_level("DEBUG", logger="alfred.storage.sqlite"):
            results = await sqlite_store.search_session_messages(
                "sess-msg",
                [1.0, 0.0, 0.0],
                top_k=2,
            )

        assert [row["message_idx"] for row in results] == [0, 1]
        assert results[0]["similarity"] > results[1]["similarity"], (
            "Message search must return higher-is-better similarity, not raw distance"
        )

        storage_messages = [record.message for record in caplog.records if record.name == "alfred.storage.sqlite"]
        assert any(message.startswith("event=storage.session_message_search.start") for message in storage_messages)
        assert any(message.startswith("event=storage.session_message_search.completed") for message in storage_messages)
        assert any("result_count=2" in message for message in storage_messages)
        assert any("duration_ms=" in message for message in storage_messages)
