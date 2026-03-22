"""Regression tests for SQLiteMemoryStore auto-rebuilding stale vec0 tables."""

from __future__ import annotations

import json
from pathlib import Path

import aiosqlite
import pytest

from alfred.config import Config
from alfred.embeddings.provider import EmbeddingProvider
from alfred.memory import create_memory_store
from alfred.storage.sqlite import SQLiteStore


class StaticEmbedder(EmbeddingProvider):
    """Deterministic embedder for rebuild regression tests."""

    @property
    def dimension(self) -> int:
        return 3

    async def embed(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def _make_config(tmp_path: Path) -> Config:
    data_dir = tmp_path / "data"
    workspace_dir = tmp_path / "workspace"
    memory_dir = tmp_path / "memory"
    data_dir.mkdir()
    workspace_dir.mkdir()
    memory_dir.mkdir()

    return Config(
        telegram_bot_token="test-token",
        openai_api_key="test-openai-key",
        kimi_api_key="test-kimi-key",
        kimi_base_url="https://example.invalid",
        data_dir=data_dir,
        workspace_dir=workspace_dir,
        memory_dir=memory_dir,
    )


@pytest.mark.asyncio
async def test_create_memory_store_rebuilds_stale_vec0_schema_without_injecting_embedder(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale memory_embeddings vec0 schema should be rebuilt by SQLiteMemoryStore."""
    config = _make_config(tmp_path)
    embedder = StaticEmbedder()

    seed_store = SQLiteStore(
        config.data_dir / "memories.db",
        embedding_dim=embedder.dimension,
        embedder=embedder,
    )
    await seed_store.add_memory(
        entry_id="mem-1",
        role="system",
        content="hello cosine rebuild",
        embedding=[1.0, 0.0, 0.0],
        tags=[],
        permanent=False,
    )

    async with aiosqlite.connect(seed_store.db_path) as db:
        await seed_store._load_extensions(db)
        await db.execute("DROP TABLE memory_embeddings")
        await db.execute(
            """
            CREATE VIRTUAL TABLE memory_embeddings USING vec0(
                entry_id TEXT PRIMARY KEY,
                embedding FLOAT[3]
            )
            """
        )
        await db.execute(
            "INSERT INTO memory_embeddings (entry_id, embedding) VALUES (?, ?)",
            ("mem-1", json.dumps([1.0, 0.0, 0.0])),
        )
        await db.commit()

    recorded_embedder: dict[str, EmbeddingProvider | None] = {}
    real_init = SQLiteStore.__init__

    def recording_init(
        self: SQLiteStore,
        db_path: Path | str,
        embedding_dim: int = 768,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        recorded_embedder["value"] = embedder
        real_init(self, db_path, embedding_dim=embedding_dim, embedder=None)

    monkeypatch.setattr(SQLiteStore, "__init__", recording_init)

    memory_store = create_memory_store(config, embedder)

    assert recorded_embedder["value"] is None

    with caplog.at_level("WARNING"):
        entries, similarities, scores = await memory_store.search(
            "hello cosine rebuild",
            top_k=1,
        )

    assert [entry.entry_id for entry in entries] == ["mem-1"]
    assert similarities["mem-1"] == pytest.approx(1.0)
    assert scores["mem-1"] == pytest.approx(1.0)
    assert "stale memory_embeddings" in caplog.text.lower()

    async with aiosqlite.connect(seed_store.db_path) as db, db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='memory_embeddings'"
    ) as cursor:
        schema_row = await cursor.fetchone()

    assert schema_row is not None
    assert "distance_metric=cosine" in schema_row[0].lower()
