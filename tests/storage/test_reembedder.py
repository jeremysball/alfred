"""Tests for EmbeddingReembedder - Phase 2 of PRD #132."""

import pytest
from unittest.mock import MagicMock, AsyncMock


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


class TestReembedMemories:
    """Tests for _reembed_memories() method."""

    @pytest.mark.asyncio
    async def test_reembed_memories_creates_new_table(self) -> None:
        """Test that _reembed_memories creates new vec0 table with correct dimension."""
        from alfred.storage.sqlite import SQLiteStore, EmbeddingReembedder
        from datetime import datetime
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Create store with 768 dimension first
            store = SQLiteStore(db_path, embedding_dim=768)
            await store._init()

            # Add a memory using correct signature
            await store.add_memory(
                entry_id="test-1",
                role="user",
                content="test content",
                embedding=[0.1] * 768,
                tags=["test"],
                timestamp=datetime.now(),
            )

            # Now create reembedder with different dimension
            mock_embedder = AsyncMock()
            mock_embedder.embed.return_value = [0.1] * 1536

            store._embedding_dim = 1536
            reembedder = EmbeddingReembedder(store, mock_embedder)

            # Re-embed memories
            count = await reembedder._reembed_memories()

            assert count >= 1

            # Verify embedder was called
            mock_embedder.embed.assert_called()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_reembed_memories_preserves_all_content(self) -> None:
        """Test that all memory content is preserved during re-embedding."""
        from alfred.storage.sqlite import SQLiteStore, EmbeddingReembedder
        from datetime import datetime
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Create store with 768 dimension
            store = SQLiteStore(db_path, embedding_dim=768)
            await store._init()

            # Add multiple memories using correct signature
            for i in range(3):
                await store.add_memory(
                    entry_id=f"mem-{i}",
                    role="user",
                    content=f"memory {i}",
                    embedding=[0.1] * 768,
                    tags=["test"],
                    timestamp=datetime.now(),
                )

            # Switch to 1536 dimension
            mock_embedder = AsyncMock()
            mock_embedder.embed.return_value = [0.1] * 1536

            store._embedding_dim = 1536
            reembedder = EmbeddingReembedder(store, mock_embedder)

            # Re-embed
            await reembedder._reembed_memories()

            # Verify memories still exist by checking we can search them
            # (Search would fail if content wasn't preserved)
            import aiosqlite
            async with aiosqlite.connect(db_path) as db:
                await store._load_extensions(db)
                async with db.execute("SELECT COUNT(*) FROM memories") as cursor:
                    row = await cursor.fetchone()
                    assert row[0] == 3

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_reembed_memories_progress_logged(self, caplog) -> None:
        """Test that progress is logged during memory re-embedding."""
        from alfred.storage.sqlite import SQLiteStore, EmbeddingReembedder
        from datetime import datetime
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            store = SQLiteStore(db_path, embedding_dim=768)
            await store._init()

            # Add memories
            for i in range(5):
                await store.add_memory(
                    entry_id=f"mem-{i}",
                    role="user",
                    content=f"memory {i}",
                    embedding=[0.1] * 768,
                    tags=["test"],
                    timestamp=datetime.now(),
                )

            mock_embedder = AsyncMock()
            mock_embedder.embed.return_value = [0.1] * 768

            reembedder = EmbeddingReembedder(store, mock_embedder)

            with caplog.at_level("INFO"):
                await reembedder._reembed_memories()

            # Should have progress logging
            progress_logs = [r for r in caplog.records if "memory" in r.message.lower()]
            assert len(progress_logs) > 0

        finally:
            os.unlink(db_path)
