"""Tests for sqlite-vec dimension detection and management."""

import pytest


class TestGetVec0Dimension:
    """Tests for _get_vec0_dimension() method."""

    @pytest.mark.asyncio
    async def test_get_vec0_dimension_returns_none_for_missing_table(self) -> None:
        """Test that _get_vec0_dimension returns None when table doesn't exist."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(":memory:", embedding_dim=768)

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            result = await store._get_vec0_dimension(db, "nonexistent_table")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_vec0_dimension_extracts_float768(self) -> None:
        """Test extraction of FLOAT[768] dimension from vec0 table schema."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(":memory:", embedding_dim=768)

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            # Load sqlite-vec extension
            await db.enable_load_extension(True)
            import sqlite_vec

            await db.load_extension(sqlite_vec.loadable_path())

            # Create vec0 table with FLOAT[768]
            await db.execute("""
                CREATE VIRTUAL TABLE test_embeddings USING vec0(
                    id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
            """)

            # Extract dimension
            result = await store._get_vec0_dimension(db, "test_embeddings")

        assert result == 768

    @pytest.mark.asyncio
    async def test_get_vec0_dimension_extracts_float1536(self) -> None:
        """Test extraction works with different dimensions (1536)."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(":memory:", embedding_dim=1536)

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            # Load sqlite-vec extension
            await db.enable_load_extension(True)
            import sqlite_vec

            await db.load_extension(sqlite_vec.loadable_path())

            # Create vec0 table with FLOAT[1536]
            await db.execute("""
                CREATE VIRTUAL TABLE test_embeddings USING vec0(
                    id TEXT PRIMARY KEY,
                    embedding FLOAT[1536]
                )
            """)

            # Extract dimension
            result = await store._get_vec0_dimension(db, "test_embeddings")

        assert result == 1536


class TestCheckDimensionMismatch:
    """Tests for _check_dimension_mismatch() method."""

    @pytest.mark.asyncio
    async def test_check_dimension_match_when_equal(self) -> None:
        """Test that no mismatch is detected when dimensions match."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(":memory:", embedding_dim=768)

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            # Load sqlite-vec extension
            await db.enable_load_extension(True)
            import sqlite_vec

            await db.load_extension(sqlite_vec.loadable_path())

            # Create vec0 table with FLOAT[768] (matches store dimension)
            await db.execute("""
                CREATE VIRTUAL TABLE test_embeddings USING vec0(
                    id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
            """)

            # Check dimension - should return None (no mismatch)
            result = await store._check_dimension_mismatch(db, "test_embeddings")

        assert result is None

    @pytest.mark.asyncio
    async def test_check_dimension_mismatch_when_different(self) -> None:
        """Test that mismatch is detected when dimensions differ."""
        from alfred.storage.sqlite import SQLiteStore

        # Store expects 1536, but table has 768
        store = SQLiteStore(":memory:", embedding_dim=1536)

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            # Load sqlite-vec extension
            await db.enable_load_extension(True)
            import sqlite_vec

            await db.load_extension(sqlite_vec.loadable_path())

            # Create vec0 table with FLOAT[768] (different from store dimension)
            await db.execute("""
                CREATE VIRTUAL TABLE test_embeddings USING vec0(
                    id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
            """)

            # Check dimension - should return (768, 1536)
            result = await store._check_dimension_mismatch(db, "test_embeddings")

        assert result == (768, 1536)

    @pytest.mark.asyncio
    async def test_check_dimension_returns_none_for_new_table(self) -> None:
        """Test that no mismatch is returned when table doesn't exist."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(":memory:", embedding_dim=768)

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            # Check dimension for non-existent table
            result = await store._check_dimension_mismatch(db, "nonexistent_table")

        assert result is None
