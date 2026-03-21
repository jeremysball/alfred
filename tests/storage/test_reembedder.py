"""Tests for EmbeddingReembedder - Phase 2 of PRD #132."""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestEmbeddingReembedderInit:
    """Tests for EmbeddingReembedder initialization."""

    def test_reembedder_initializes_with_store_and_embedder(self) -> None:
        """Test that EmbeddingReembedder accepts store and embedder."""
        from alfred.storage.sqlite import EmbeddingReembedder

        mock_store = MagicMock()
        mock_embedder = MagicMock()

        reembedder = EmbeddingReembedder(mock_store, mock_embedder)

        assert reembedder._store is mock_store
        assert reembedder._embedder is mock_embedder


class TestReembedAll:
    """Tests for reembed_all() orchestration method."""

    @pytest.mark.asyncio
    async def test_reembed_all_detects_dimension_mismatch(self) -> None:
        """Test that reembed_all detects and reports dimension mismatch."""
        from alfred.storage.sqlite import EmbeddingReembedder

        mock_store = MagicMock()
        mock_store._embedding_dim = 768
        mock_store.db_path = ":memory:"
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = [0.1] * 768

        reembedder = EmbeddingReembedder(mock_store, mock_embedder)

        # Mock the individual re-embed methods to avoid DB operations
        reembedder._reembed_memories = AsyncMock(return_value=5)
        reembedder._reembed_session_summaries = AsyncMock(return_value=3)
        reembedder._reembed_message_embeddings = AsyncMock(return_value=10)

        # Should complete successfully
        result = await reembedder.reembed_all(old_dim=768, new_dim=1536)

        assert result.success is True
        assert "768" in result.message
        assert "1536" in result.message
        assert result.stats["memories_reembedded"] == 5

    @pytest.mark.asyncio
    async def test_reembed_all_handles_failure(self) -> None:
        """Test that reembed_all handles failures gracefully."""
        from alfred.storage.sqlite import EmbeddingReembedder

        mock_store = MagicMock()
        mock_store.db_path = ":memory:"
        mock_embedder = AsyncMock()

        reembedder = EmbeddingReembedder(mock_store, mock_embedder)

        # Mock to raise exception
        reembedder._reembed_memories = AsyncMock(side_effect=Exception("DB Error"))

        result = await reembedder.reembed_all(old_dim=768, new_dim=1536)

        assert result.success is False
        assert "failed" in result.message.lower()


class TestReembedMethods:
    """Tests for individual re-embed methods."""

    @pytest.mark.asyncio
    async def test_reembed_memories_queries_and_embeds(self) -> None:
        """Test _reembed_memories queries memories and calls embedder."""
        import os
        import tempfile

        import aiosqlite

        from alfred.storage.sqlite import EmbeddingReembedder

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Create store and tables
            from alfred.storage.sqlite import SQLiteStore
            store = SQLiteStore(db_path, embedding_dim=768)
            await store._init()

            # Check actual schema first
            async with aiosqlite.connect(db_path) as db:
                await store._load_extensions(db)
                async with db.execute("PRAGMA table_info(memories)") as cursor:
                    columns = await cursor.fetchall()
                    col_names = [c[1] for c in columns]

            # Insert test data using correct schema
            async with aiosqlite.connect(db_path) as db:
                await store._load_extensions(db)

                # Use correct column names from schema
                id_col = "entry_id" if "entry_id" in col_names else col_names[0]

                await db.execute(
                    f"""INSERT INTO memories ({id_col}, role, content)
                       VALUES (?, ?, ?)""",
                    ("mem-1", "user", "test content 1")
                )
                await db.execute(
                    f"""INSERT INTO memories ({id_col}, role, content)
                       VALUES (?, ?, ?)""",
                    ("mem-2", "assistant", "test content 2")
                )
                await db.commit()

            # Create reembedder
            mock_embedder = AsyncMock()
            mock_embedder.embed.return_value = [0.5] * 768

            reembedder = EmbeddingReembedder(store, mock_embedder)

            # Re-embed
            count = await reembedder._reembed_memories()

            # Should process 2 memories
            assert count == 2
            assert mock_embedder.embed.call_count == 2

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_reembed_session_summaries_queries_and_embeds(self) -> None:
        """Test _reembed_session_summaries queries and re-embeds."""
        import os
        import tempfile

        import aiosqlite

        from alfred.storage.sqlite import EmbeddingReembedder, SQLiteStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            store = SQLiteStore(db_path, embedding_dim=768)
            await store._init()

            # Insert test data (include required columns)
            async with aiosqlite.connect(db_path) as db:
                await store._load_extensions(db)
                await db.execute(
                    """INSERT INTO session_summaries
                       (summary_id, session_id, message_count, first_message_idx, last_message_idx, summary_text)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    ("sum-1", "session-1", 5, 0, 4, "summary 1")
                )
                await db.execute(
                    """INSERT INTO session_summaries
                       (summary_id, session_id, message_count, first_message_idx, last_message_idx, summary_text)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    ("sum-2", "session-2", 3, 0, 2, "summary 2")
                )
                await db.commit()

            mock_embedder = AsyncMock()
            mock_embedder.embed.return_value = [0.5] * 768

            reembedder = EmbeddingReembedder(store, mock_embedder)
            count = await reembedder._reembed_session_summaries()

            assert count == 2
            assert mock_embedder.embed.call_count == 2

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_reembed_message_embeddings_queries_and_embeds(self) -> None:
        """Test _reembed_message_embeddings queries and re-embeds."""
        import os
        import tempfile

        import aiosqlite

        from alfred.storage.sqlite import EmbeddingReembedder, SQLiteStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            store = SQLiteStore(db_path, embedding_dim=768)
            await store._init()

            # Insert test data
            async with aiosqlite.connect(db_path) as db:
                await store._load_extensions(db)
                await db.execute(
                    """INSERT INTO message_embeddings
                       (message_embedding_id, session_id, message_idx, role, content_snippet, embedding)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    ("msg-1", "session-1", 0, "user", "snippet 1", "[0.1, 0.2]")
                )
                await db.execute(
                    """INSERT INTO message_embeddings
                       (message_embedding_id, session_id, message_idx, role, content_snippet, embedding)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    ("msg-2", "session-1", 1, "assistant", "snippet 2", "[0.3, 0.4]")
                )
                await db.commit()

            mock_embedder = AsyncMock()
            mock_embedder.embed.return_value = [0.5] * 768

            reembedder = EmbeddingReembedder(store, mock_embedder)
            count = await reembedder._reembed_message_embeddings()

            assert count == 2
            assert mock_embedder.embed.call_count == 2

        finally:
            os.unlink(db_path)
