"""Integration regression for shared similarity direction across memory and session search."""

from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import aiosqlite
import pytest

from alfred.config import Config
from alfred.context import ContextBuilder
from alfred.embeddings.provider import EmbeddingProvider
from alfred.memory import MemoryEntry
from alfred.memory.sqlite_store import SQLiteMemoryStore
from alfred.storage.sqlite import SQLiteStore
from alfred.tools.search_sessions import SearchSessionsTool, SessionSummarizer


class DirectionalEmbeddingProvider(EmbeddingProvider):
    """Deterministic 2D embeddings that make similarity direction obvious."""

    @property
    def dimension(self) -> int:
        return 2

    def _vector_for(self, text: str) -> list[float]:
        normalized = text.lower()
        if "favorite color" in normalized or "blue" in normalized:
            return [1.0, 0.0]
        if "favorite food" in normalized or "pizza" in normalized:
            return [0.0, 1.0]
        return [0.70710678, 0.70710678]

    async def embed(self, text: str) -> list[float]:
        return self._vector_for(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for(text) for text in texts]


@pytest.fixture
def config(tmp_path) -> Config:
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


async def _collect_stream(tool: SearchSessionsTool, **kwargs: Any) -> str:
    chunks: list[str] = []
    async for chunk in tool.execute_stream(**kwargs):
        chunks.append(chunk)
    return "".join(chunks)


@pytest.mark.asyncio
async def test_memory_and_session_search_share_the_same_similarity_direction(
    config: Config,
) -> None:
    """The best semantic match must stay highest across memory and session search."""
    embedder = DirectionalEmbeddingProvider()
    query_text = "what is my favorite color?"
    query_embedding = await embedder.embed(query_text)

    memory_store = SQLiteMemoryStore(config, embedder)
    await memory_store.add_entries(
        [
            MemoryEntry(
                entry_id="mem-blue",
                content="My favorite color is blue",
                timestamp=datetime.now(),
                role="system",
            ),
            MemoryEntry(
                entry_id="mem-pizza",
                content="My favorite food is pizza",
                timestamp=datetime.now(),
                role="system",
            ),
        ]
    )

    memory_results, memory_similarities, memory_scores = await memory_store.search(
        query_text,
        top_k=2,
    )
    assert [entry.entry_id for entry in memory_results] == ["mem-blue", "mem-pizza"]
    assert memory_similarities["mem-blue"] > memory_similarities["mem-pizza"]
    assert memory_similarities["mem-blue"] == pytest.approx(1.0)
    assert memory_similarities["mem-pizza"] == pytest.approx(0.0)
    assert memory_scores["mem-blue"] > memory_scores["mem-pizza"]

    context_builder = ContextBuilder(
        store=memory_store._store,
        memory_budget=32000,
        min_similarity=0.6,
    )
    context_memories, context_similarities, context_scores = await context_builder.search_memories(
        query_embedding,
        top_k=2,
    )
    assert [entry.entry_id for entry in context_memories] == ["mem-blue"]
    assert context_similarities["mem-blue"] == pytest.approx(1.0)
    assert context_scores["mem-blue"] == pytest.approx(1.0)
    assert "mem-pizza" not in context_similarities

    session_store = SQLiteStore(
        config.data_dir / "sessions.db",
        embedding_dim=embedder.dimension,
        embedder=embedder,
    )
    blue_embedding = await embedder.embed("My favorite color is blue")
    pizza_embedding = await embedder.embed("My favorite food is pizza")

    await session_store._init()
    async with aiosqlite.connect(session_store.db_path) as db:
        await session_store._load_extensions(db)
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "INSERT INTO sessions (session_id, messages) VALUES (?, ?)",
            ("session-blue", json.dumps([])),
        )
        await db.execute(
            "INSERT INTO sessions (session_id, messages) VALUES (?, ?)",
            ("session-pizza", json.dumps([])),
        )
        await db.execute(
            """
            INSERT INTO session_summaries (
                summary_id, session_id, message_count,
                first_message_idx, last_message_idx, summary_text, embedding, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "summary-blue",
                "session-blue",
                2,
                0,
                1,
                "My favorite color is blue",
                json.dumps(blue_embedding),
                1,
            ),
        )
        await db.execute(
            """
            INSERT INTO session_summaries (
                summary_id, session_id, message_count,
                first_message_idx, last_message_idx, summary_text, embedding, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "summary-pizza",
                "session-pizza",
                1,
                0,
                0,
                "My favorite food is pizza",
                json.dumps(pizza_embedding),
                1,
            ),
        )
        await db.execute(
            "INSERT INTO session_summaries_vec (summary_id, embedding) VALUES (?, ?)",
            ("summary-blue", json.dumps(blue_embedding)),
        )
        await db.execute(
            "INSERT INTO session_summaries_vec (summary_id, embedding) VALUES (?, ?)",
            ("summary-pizza", json.dumps(pizza_embedding)),
        )
        await db.execute(
            """
            INSERT INTO message_embeddings (
                message_embedding_id, session_id, message_idx,
                role, content_snippet, embedding
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "session-blue_0",
                "session-blue",
                0,
                "user",
                "My favorite color is blue",
                json.dumps(blue_embedding),
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
                "session-blue_1",
                "session-blue",
                1,
                "assistant",
                "Pizza is not the answer here",
                json.dumps(pizza_embedding),
            ),
        )
        await db.execute(
            "INSERT INTO message_embeddings_vec (message_embedding_id, embedding) VALUES (?, ?)",
            ("session-blue_0", json.dumps(blue_embedding)),
        )
        await db.execute(
            "INSERT INTO message_embeddings_vec (message_embedding_id, embedding) VALUES (?, ?)",
            ("session-blue_1", json.dumps(pizza_embedding)),
        )
        await db.commit()

    summary_results = await session_store.search_summaries(query_embedding, top_k=2)
    assert [row["session_id"] for row in summary_results] == [
        "session-blue",
        "session-pizza",
    ]
    assert summary_results[0]["similarity"] > summary_results[1]["similarity"]
    assert summary_results[0]["similarity"] == pytest.approx(1.0)
    assert summary_results[1]["similarity"] == pytest.approx(0.0)

    message_results = await session_store.search_session_messages(
        "session-blue",
        query_embedding,
        top_k=2,
    )
    assert [row["message_idx"] for row in message_results] == [0, 1]
    assert message_results[0]["similarity"] > message_results[1]["similarity"]
    assert message_results[0]["similarity"] == pytest.approx(1.0)
    assert message_results[1]["similarity"] == pytest.approx(0.0)

    summarizer = SessionSummarizer(
        llm_client=SimpleNamespace(),
        embedder=embedder,
        store=session_store,
    )
    tool = SearchSessionsTool(
        embedder=embedder,
        summarizer=summarizer,
        min_similarity=0.6,
    )
    output = await _collect_stream(
        tool,
        query=query_text,
        top_k=2,
        messages_per_session=1,
    )

    assert "session-blue" in output
    assert "Relevance: 1.00" in output
    assert "session-pizza" not in output
    assert "pizza" not in output.lower()
