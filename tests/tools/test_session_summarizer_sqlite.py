"""Tests for SessionSummarizer with real SQLiteStore integration."""

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from alfred.session import Message, Role, Session, SessionMeta
from alfred.storage.sqlite import SQLiteStore
from alfred.tools.search_sessions import SessionSummarizer, SessionSummary


@pytest.fixture
async def sqlite_store(tmp_path: Path) -> SQLiteStore:
    """Create real SQLiteStore for testing."""
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path)
    await store._init()
    return store


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""

    class MockLLM:
        async def generate_summary(self, preview: str) -> str:
            return f"Summary of: {preview[:50]}..."

    return MockLLM()


@pytest.fixture
def mock_embedder():
    """Create mock embedder."""

    class MockEmbedder:
        async def embed(self, text: str) -> list[float]:
            return [0.1] * 768

    return MockEmbedder()


class TestSessionSummarizerSQLite:
    """Tests for SessionSummarizer using real SQLiteStore."""

    @pytest.mark.asyncio
    async def test_save_summary_to_sqlite(self, sqlite_store, mock_llm_client, mock_embedder, tmp_path):
        """Verify save_summary persists to SQLite."""
        summarizer = SessionSummarizer(mock_llm_client, mock_embedder, store=sqlite_store)

        # Create parent session first
        import aiosqlite

        async with aiosqlite.connect(sqlite_store.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                "INSERT INTO sessions (session_id, messages, message_count) VALUES (?, ?, ?)",
                ("sess_001", "[]", 5),
            )
            await db.commit()

        # Create and save summary
        summary = SessionSummary(
            session_id="sess_001",
            text="Test conversation summary",
            embedding=[0.1] * 768,
            message_count=5,
            created_at=datetime(2026, 3, 7, 10, 0, 0, tzinfo=UTC),
        )

        await summarizer.save_summary(summary)

        # Verify in database
        async with (
            aiosqlite.connect(sqlite_store.db_path) as db,
            db.execute(
                "SELECT summary_text, message_count FROM session_summaries WHERE session_id = ?",
                ("sess_001",),
            ) as cursor,
        ):
            row = await cursor.fetchone()
            assert row[0] == "Test conversation summary"
            assert row[1] == 5

    @pytest.mark.asyncio
    async def test_load_summary_from_sqlite(self, sqlite_store, mock_llm_client, mock_embedder):
        """Verify load_summary retrieves from SQLite."""
        summarizer = SessionSummarizer(mock_llm_client, mock_embedder, store=sqlite_store)

        # Insert session and summary directly
        import aiosqlite

        async with aiosqlite.connect(sqlite_store.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                "INSERT INTO sessions (session_id, messages, message_count) VALUES (?, ?, ?)",
                ("sess_002", "[]", 3),
            )
            await db.execute(
                """
                INSERT INTO session_summaries
                (summary_id, session_id, message_count, first_message_idx, last_message_idx,
                 summary_text, embedding, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("sum_002", "sess_002", 3, 0, 2, "Loaded summary", json.dumps([0.4] * 768), 1),
            )
            await db.commit()

        # Load via summarizer
        loaded = await summarizer.load_summary("sess_002")

        assert loaded is not None
        assert loaded.text == "Loaded summary"
        assert loaded.session_id == "sess_002"
        assert loaded.embedding == [0.4] * 768

    @pytest.mark.asyncio
    async def test_load_summary_none_exists(self, sqlite_store, mock_llm_client, mock_embedder):
        """Verify load_summary returns None when no summary exists."""
        summarizer = SessionSummarizer(mock_llm_client, mock_embedder, store=sqlite_store)

        loaded = await summarizer.load_summary("sess_nonexistent")

        assert loaded is None

    @pytest.mark.asyncio
    async def test_save_summary_embedding_serialization(self, sqlite_store, mock_llm_client, mock_embedder):
        """Verify embedding is serialized to JSON in SQLite."""
        summarizer = SessionSummarizer(mock_llm_client, mock_embedder, store=sqlite_store)

        import aiosqlite

        async with aiosqlite.connect(sqlite_store.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                "INSERT INTO sessions (session_id, messages, message_count) VALUES (?, ?, ?)",
                ("sess_003", "[]", 2),
            )
            await db.commit()

        summary = SessionSummary(
            session_id="sess_003",
            text="Embedding test",
            embedding=[0.9] * 768,
            message_count=2,
        )

        await summarizer.save_summary(summary)

        # Verify embedding stored as JSON
        async with (
            aiosqlite.connect(sqlite_store.db_path) as db,
            db.execute("SELECT embedding FROM session_summaries WHERE session_id = ?", ("sess_003",)) as cursor,
        ):
            row = await cursor.fetchone()
            stored = json.loads(row[0])
            assert stored == [0.9] * 768

    @pytest.mark.asyncio
    async def test_generate_summary_uses_message_chunks(self, sqlite_store, mock_embedder):
        """Verify long sessions are summarized chunk by chunk."""

        class RecordingLLM:
            def __init__(self) -> None:
                self.prompts: list[str] = []

            async def chat(self, messages):
                prompt = messages[1].content
                self.prompts.append(prompt)
                if "Chunk summaries:" in prompt:
                    return SimpleNamespace(content="final summary")
                if "message-10" in prompt:
                    return SimpleNamespace(content="second chunk summary")
                return SimpleNamespace(content="first chunk summary")

        llm_client = RecordingLLM()
        summarizer = SessionSummarizer(llm_client, mock_embedder, store=sqlite_store)

        messages = [
            Message(
                idx=index,
                role=Role.USER if index % 2 == 0 else Role.ASSISTANT,
                content=f"message-{index}",
            )
            for index in range(11)
        ]
        session = Session(
            meta=SessionMeta(
                session_id="sess_chunked",
                created_at=datetime(2026, 3, 7, 10, 0, 0, tzinfo=UTC),
                last_active=datetime(2026, 3, 7, 10, 5, 0, tzinfo=UTC),
                status="active",
            ),
            messages=messages,
        )

        summary = await summarizer.generate_summary(session)

        assert summary.text == "final summary"
        assert len(llm_client.prompts) == 3
        assert any("message-10" in prompt for prompt in llm_client.prompts)

    @pytest.mark.asyncio
    async def test_save_summary_without_store_raises(self, mock_llm_client, mock_embedder):
        """Verify save_summary raises error when no store configured."""
        summarizer = SessionSummarizer(mock_llm_client, mock_embedder, store=None)

        summary = SessionSummary(
            session_id="sess_004",
            text="No store",
            message_count=1,
        )

        with pytest.raises(RuntimeError, match="SQLiteStore not configured"):
            await summarizer.save_summary(summary)
