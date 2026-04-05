"""Tests for sqlite-vec dimension detection and management."""

import pytest


class TestGetVec0Metric:
    """Tests for _get_vec0_metric() method."""

    @pytest.mark.asyncio
    async def test_get_vec0_metric_returns_none_for_missing_table(self) -> None:
        """Test that _get_vec0_metric returns None when table doesn't exist."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(":memory:", embedding_dim=768)

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            result = await store._get_vec0_metric(db, "nonexistent_table")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_vec0_metric_detects_cosine_configuration(self) -> None:
        """Test extraction of distance_metric=cosine from vec0 table schema."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(":memory:", embedding_dim=768)

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            await db.enable_load_extension(True)
            import sqlite_vec

            await db.load_extension(sqlite_vec.loadable_path())

            await db.execute("""
                CREATE VIRTUAL TABLE test_embeddings USING vec0(
                    id TEXT PRIMARY KEY,
                    embedding FLOAT[768] distance_metric=cosine
                )
            """)

            result = await store._get_vec0_metric(db, "test_embeddings")

        assert result == "cosine"


class TestGetVec0SchemaMismatch:
    """Tests for vec schema mismatch detection."""

    @pytest.mark.asyncio
    async def test_vec_schema_validation_detects_metric_drift_with_matching_dimension(
        self,
    ) -> None:
        """A vec0 table with the right dimension but wrong metric is drifted."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(":memory:", embedding_dim=768)

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            await db.enable_load_extension(True)
            import sqlite_vec

            await db.load_extension(sqlite_vec.loadable_path())

            await db.execute("""
                CREATE VIRTUAL TABLE test_embeddings USING vec0(
                    id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
            """)

            result = await store._check_vec0_schema_mismatch(db, "test_embeddings")

        assert result == (768, "l2", 768, "cosine")


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


class TestVecTableCreationContract:
    """Tests for vec0 table creation contract."""

    @pytest.mark.asyncio
    async def test_all_vec_tables_are_created_with_cosine_metric_contract(self, tmp_path) -> None:
        """All Alfred vec0 tables should be created with cosine semantics."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(tmp_path / "vec-contract.db", embedding_dim=768)
        await store._init()

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='memory_embeddings'") as cursor:
                memory_schema = (await cursor.fetchone())[0]
            async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='session_summaries_vec'") as cursor:
                summary_schema = (await cursor.fetchone())[0]
            async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='message_embeddings_vec'") as cursor:
                message_schema = (await cursor.fetchone())[0]

        assert "distance_metric=cosine" in memory_schema.lower()
        assert "distance_metric=cosine" in summary_schema.lower()
        assert "distance_metric=cosine" in message_schema.lower()


class TestInitSchemaGuardrails:
    """Tests for startup guardrails around vec0 schema drift."""

    @pytest.mark.asyncio
    async def test_store_init_automatically_rebuilds_metric_drift_when_embedder_available(
        self,
        tmp_path,
        caplog,
    ) -> None:
        """Existing vec0 tables without cosine should be rebuilt on init."""
        import json

        import aiosqlite

        from alfred.storage.sqlite import SQLiteStore

        class StaticEmbedder:
            dimension = 3

            async def embed(self, text: str) -> list[float]:
                return [1.0, 0.0, 0.0]

        embedder = StaticEmbedder()
        store = SQLiteStore(tmp_path / "drift.db", embedding_dim=3, embedder=embedder)
        await store._init()

        async with aiosqlite.connect(store.db_path) as db:
            await store._load_extensions(db)
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                "INSERT INTO sessions (session_id) VALUES (?)",
                ("session-1",),
            )
            await db.execute(
                """
                INSERT INTO memories (entry_id, role, content, tags, permanent)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "mem-1",
                    "system",
                    "hello cosine rebuild",
                    "[]",
                    0,
                ),
            )
            await db.execute(
                """
                INSERT INTO session_summaries (
                    summary_id, session_id, message_count,
                    first_message_idx, last_message_idx, summary_text,
                    embedding, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "sum-1",
                    "session-1",
                    1,
                    0,
                    0,
                    "hello cosine rebuild",
                    json.dumps([1.0, 0.0, 0.0]),
                    1,
                ),
            )
            await db.execute(
                """
                INSERT INTO session_messages (session_id, message_id, message_idx, role, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("session-1", "msg-0", 0, "user", '{"role": "user", "content": "hello cosine rebuild"}'),
            )
            await db.execute(
                """
                INSERT INTO message_embeddings (
                    message_embedding_id, session_id, message_id, message_idx,
                    role, content_snippet, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "session-1_0",
                    "session-1",
                    "msg-0",
                    0,
                    "user",
                    "hello cosine rebuild",
                    json.dumps([1.0, 0.0, 0.0]),
                ),
            )
            await db.execute("DROP TABLE memory_embeddings")
            await db.execute("DROP TABLE session_summaries_vec")
            await db.execute("DROP TABLE message_embeddings_vec")
            await db.execute(
                """
                CREATE VIRTUAL TABLE memory_embeddings USING vec0(
                    entry_id TEXT PRIMARY KEY,
                    embedding FLOAT[3]
                )
                """
            )
            await db.execute(
                """
                CREATE VIRTUAL TABLE session_summaries_vec USING vec0(
                    summary_id TEXT PRIMARY KEY,
                    embedding FLOAT[3]
                )
                """
            )
            await db.execute(
                """
                CREATE VIRTUAL TABLE message_embeddings_vec USING vec0(
                    message_embedding_id TEXT PRIMARY KEY,
                    embedding FLOAT[3]
                )
                """
            )
            await db.commit()

        rebuilt_store = SQLiteStore(tmp_path / "drift.db", embedding_dim=3, embedder=embedder)

        with caplog.at_level("WARNING"):
            await rebuilt_store._init()

        assert "automatic rebuild" in caplog.text.lower()

        import aiosqlite

        async with aiosqlite.connect(rebuilt_store.db_path) as db:
            async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='memory_embeddings'") as cursor:
                memory_schema = (await cursor.fetchone())[0]
            async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='session_summaries_vec'") as cursor:
                summary_schema = (await cursor.fetchone())[0]
            async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='message_embeddings_vec'") as cursor:
                message_schema = (await cursor.fetchone())[0]

        assert "distance_metric=cosine" in memory_schema.lower()
        assert "distance_metric=cosine" in summary_schema.lower()
        assert "distance_metric=cosine" in message_schema.lower()

        memory_results = await rebuilt_store.search_memories([1.0, 0.0, 0.0], top_k=1)
        summary_results = await rebuilt_store.search_summaries([1.0, 0.0, 0.0], top_k=1)
        message_results = await rebuilt_store.search_session_messages(
            "session-1",
            [1.0, 0.0, 0.0],
            top_k=1,
        )

        assert [row["entry_id"] for row in memory_results] == ["mem-1"]
        assert memory_results[0]["similarity"] > 0.9
        assert [row["summary_id"] for row in summary_results] == ["sum-1"]
        assert summary_results[0]["similarity"] > 0.9
        assert [row["message_idx"] for row in message_results] == [0]
        assert message_results[0]["similarity"] > 0.9

    @pytest.mark.asyncio
    async def test_store_init_automatically_rebuilds_session_metric_drift_without_embedder(
        self,
        tmp_path,
        caplog,
    ) -> None:
        """Session/message vec drift should auto-rebuild even without an embedder."""
        import json

        import aiosqlite

        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(tmp_path / "drift-sessions.db", embedding_dim=3)
        await store._init()

        async with aiosqlite.connect(store.db_path) as db:
            await store._load_extensions(db)
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                "INSERT INTO sessions (session_id) VALUES (?)",
                ("session-1",),
            )
            await db.execute(
                """
                INSERT INTO session_summaries (
                    summary_id, session_id, message_count,
                    first_message_idx, last_message_idx, summary_text,
                    embedding, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "sum-1",
                    "session-1",
                    1,
                    0,
                    0,
                    "hello cosine rebuild",
                    json.dumps([1.0, 0.0, 0.0]),
                    1,
                ),
            )
            await db.execute(
                """
                INSERT INTO session_messages (session_id, message_id, message_idx, role, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("session-1", "msg-0", 0, "user", '{"role": "user", "content": "hello cosine rebuild"}'),
            )
            await db.execute(
                """
                INSERT INTO message_embeddings (
                    message_embedding_id, session_id, message_id, message_idx,
                    role, content_snippet, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "session-1_0",
                    "session-1",
                    "msg-0",
                    0,
                    "user",
                    "hello cosine rebuild",
                    json.dumps([1.0, 0.0, 0.0]),
                ),
            )
            await db.execute("DROP TABLE session_summaries_vec")
            await db.execute("DROP TABLE message_embeddings_vec")
            await db.execute(
                """
                CREATE VIRTUAL TABLE session_summaries_vec USING vec0(
                    summary_id TEXT PRIMARY KEY,
                    embedding FLOAT[3]
                )
                """
            )
            await db.execute(
                """
                CREATE VIRTUAL TABLE message_embeddings_vec USING vec0(
                    message_embedding_id TEXT PRIMARY KEY,
                    embedding FLOAT[3]
                )
                """
            )
            await db.commit()

        rebuilt_store = SQLiteStore(tmp_path / "drift-sessions.db", embedding_dim=3)

        with caplog.at_level("WARNING"):
            await rebuilt_store._init()

        assert "automatic vec0 rebuild" in caplog.text.lower()

        async with aiosqlite.connect(rebuilt_store.db_path) as db:
            async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='session_summaries_vec'") as cursor:
                summary_schema = (await cursor.fetchone())[0]
            async with db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='message_embeddings_vec'") as cursor:
                message_schema = (await cursor.fetchone())[0]

        assert "distance_metric=cosine" in summary_schema.lower()
        assert "distance_metric=cosine" in message_schema.lower()

        summary_results = await rebuilt_store.search_summaries([1.0, 0.0, 0.0], top_k=1)
        message_results = await rebuilt_store.search_session_messages(
            "session-1",
            [1.0, 0.0, 0.0],
            top_k=1,
        )

        assert [row["summary_id"] for row in summary_results] == ["sum-1"]
        assert summary_results[0]["similarity"] > 0.9
        assert [row["message_idx"] for row in message_results] == [0]
        assert message_results[0]["similarity"] > 0.9

    @pytest.mark.asyncio
    async def test_store_init_rejects_metric_mismatch_when_rebuild_is_unavailable(
        self,
        tmp_path,
    ) -> None:
        """Existing vec0 tables without cosine should fail clearly on init."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(tmp_path / "drift.db", embedding_dim=768)

        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            await db.enable_load_extension(True)
            import sqlite_vec

            await db.load_extension(sqlite_vec.loadable_path())
            await db.execute("""
                CREATE VIRTUAL TABLE memory_embeddings USING vec0(
                    entry_id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
            """)
            await db.commit()

        with pytest.raises(RuntimeError, match="vec0 schema mismatch.*memory_embeddings"):
            await store._init()


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


class TestInitDimensionDetection:
    """Tests for dimension detection during SQLiteStore initialization."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_init_detects_dimension_mismatch_on_startup(self, caplog):
        """Test that dimension mismatch is detected and logged during init."""
        import os
        import tempfile

        from alfred.storage.sqlite import SQLiteStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # First store creates tables with 768
            store1 = SQLiteStore(db_path, embedding_dim=768)
            await store1._init()

            # Second store expects 1536 - should detect mismatch
            store2 = SQLiteStore(db_path, embedding_dim=1536)

            with caplog.at_level("WARNING"):
                await store2._init()

            # Verify warning was logged
            assert "768" in caplog.text and "1536" in caplog.text

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_dimension_check_skipped_when_match(self, caplog):
        """Test that no warning is logged when dimensions match."""
        from alfred.storage.sqlite import SQLiteStore

        store = SQLiteStore(":memory:", embedding_dim=768)

        with caplog.at_level("WARNING"):
            await store._init()

        # Should not have dimension mismatch warnings
        dim_warnings = [r for r in caplog.records if "dimension changed" in r.message.lower()]
        assert len(dim_warnings) == 0


class TestAllVec0Tables:
    """Tests for checking all three vec0 tables."""

    @pytest.mark.asyncio
    async def test_checks_all_vec0_tables(self, caplog):
        """Test that dimension check runs for all three vec0 tables."""
        import os
        import tempfile

        from alfred.storage.sqlite import SQLiteStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # First store creates tables with 768
            store1 = SQLiteStore(db_path, embedding_dim=768)
            await store1._init()

            # Second store expects 1536 - should detect mismatch in all tables
            store2 = SQLiteStore(db_path, embedding_dim=1536)

            with caplog.at_level("WARNING"):
                await store2._init()

            # Verify all three tables are mentioned
            assert "memory_embeddings" in caplog.text
            assert "message_embeddings_vec" in caplog.text
            assert "session_summaries_vec" in caplog.text

        finally:
            os.unlink(db_path)


class TestVecTableRebuild:
    """Tests for vec0 rebuild orchestration."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_rebuild_vector_indexes_recreates_all_metric_drifted_vec_tables(
        self,
        tmp_path,
    ) -> None:
        """Rebuild should restore cosine metric on every vec0 table."""
        from unittest.mock import AsyncMock

        import aiosqlite

        from alfred.storage.sqlite import SQLiteStore

        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = [0.1] * 768

        store = SQLiteStore(
            tmp_path / "vec-rebuild.db",
            embedding_dim=768,
            embedder=mock_embedder,
        )
        await store._init()

        async with aiosqlite.connect(store.db_path) as db:
            await store._load_extensions(db)
            await db.execute("DROP TABLE memory_embeddings")
            await db.execute("DROP TABLE session_summaries_vec")
            await db.execute("DROP TABLE message_embeddings_vec")
            await db.execute(
                """
                CREATE VIRTUAL TABLE memory_embeddings USING vec0(
                    entry_id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
                """
            )
            await db.execute(
                """
                CREATE VIRTUAL TABLE session_summaries_vec USING vec0(
                    summary_id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
                """
            )
            await db.execute(
                """
                CREATE VIRTUAL TABLE message_embeddings_vec USING vec0(
                    message_embedding_id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
                """
            )
            await db.commit()

        await store.rebuild_vector_indexes()

        async with aiosqlite.connect(store.db_path) as db:
            for table_name in (
                "memory_embeddings",
                "session_summaries_vec",
                "message_embeddings_vec",
            ):
                async with db.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,),
                ) as cursor:
                    row = await cursor.fetchone()

                assert row is not None
                assert row[0] is not None
                assert "distance_metric=cosine" in row[0].lower()

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_rebuild_vector_indexes_repopulates_memory_embeddings(self, tmp_path) -> None:
        """Rebuilt memory vectors should be searchable again."""
        from unittest.mock import AsyncMock

        import aiosqlite

        from alfred.storage.sqlite import SQLiteStore

        query_embedding = [1.0] + [0.0] * 767
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = query_embedding

        store = SQLiteStore(
            tmp_path / "vec-rebuild-memory.db",
            embedding_dim=768,
            embedder=mock_embedder,
        )
        await store._init()

        async with aiosqlite.connect(store.db_path) as db:
            await store._load_extensions(db)
            await db.execute(
                """
                INSERT INTO memories (entry_id, role, content, tags, permanent)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "mem-1",
                    "user",
                    "hello cosine rebuild",
                    '["migration"]',
                    0,
                ),
            )
            await db.execute("DROP TABLE memory_embeddings")
            await db.execute(
                """
                CREATE VIRTUAL TABLE memory_embeddings USING vec0(
                    entry_id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
                """
            )
            await db.commit()

        await store.rebuild_vector_indexes()

        results = await store.search_memories(query_embedding, top_k=5)

        assert [row["entry_id"] for row in results] == ["mem-1"]
        assert results[0]["similarity"] > 0.9

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_rebuild_vector_indexes_repopulates_session_summary_and_message_vec_tables(
        self,
        tmp_path,
    ) -> None:
        """Rebuilt summary and message vectors should still be searchable."""
        import json

        import aiosqlite

        from alfred.storage.sqlite import SQLiteStore

        query_embedding = [1.0] + [0.0] * 767
        embedding_json = json.dumps(query_embedding)

        store = SQLiteStore(tmp_path / "vec-rebuild-session.db", embedding_dim=768)
        await store._init()

        async with aiosqlite.connect(store.db_path) as db:
            await store._load_extensions(db)
            await db.execute(
                """
                INSERT INTO sessions (session_id, message_count, metadata)
                VALUES (?, ?, ?)
                """,
                ("session-1", 2, "{}"),
            )
            await db.execute(
                """
                INSERT INTO session_summaries (
                    summary_id, session_id, message_count,
                    first_message_idx, last_message_idx, summary_text,
                    embedding, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "sum-1",
                    "session-1",
                    2,
                    0,
                    1,
                    "cosine summary",
                    embedding_json,
                    1,
                ),
            )
            await db.execute(
                """
                INSERT INTO session_messages (session_id, message_id, message_idx, role, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("session-1", "msg-1", 0, "user", '{"role": "user", "content": "cosine snippet"}'),
            )
            await db.execute(
                """
                INSERT INTO message_embeddings (
                    message_embedding_id, session_id, message_id, message_idx,
                    role, content_snippet, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "msg-1",
                    "session-1",
                    "msg-1",
                    0,
                    "user",
                    "cosine snippet",
                    embedding_json,
                ),
            )
            await db.execute("DROP TABLE session_summaries_vec")
            await db.execute("DROP TABLE message_embeddings_vec")
            await db.execute(
                """
                CREATE VIRTUAL TABLE session_summaries_vec USING vec0(
                    summary_id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
                """
            )
            await db.execute(
                """
                CREATE VIRTUAL TABLE message_embeddings_vec USING vec0(
                    message_embedding_id TEXT PRIMARY KEY,
                    embedding FLOAT[768]
                )
                """
            )
            await db.commit()

        await store.rebuild_vector_indexes()

        summary_results = await store.search_summaries(query_embedding, top_k=1)
        message_results = await store.search_session_messages(
            "session-1",
            query_embedding,
            top_k=1,
        )

        assert [row["summary_id"] for row in summary_results] == ["sum-1"]
        assert summary_results[0]["similarity"] > 0.9
        assert [row["message_idx"] for row in message_results] == [0]
        assert message_results[0]["similarity"] > 0.9
