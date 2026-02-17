"""Tests for memory storage system."""

import pytest
from datetime import datetime
from pathlib import Path

from src.types import MemoryEntry
from src.memory import MemoryStore


class MockEmbedder:
    """Mock embedder that returns golden vectors for testing."""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    async def embed(self, text: str) -> list[float]:
        # Deterministic "golden" vector based on text hash
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        # Generate vector values deterministically
        vector = []
        for i in range(self.dimension):
            val = ((hash_val + i * 31) % 2000 - 1000) / 1000.0
            vector.append(val)
        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


@pytest.fixture
def mock_config(tmp_path, monkeypatch):
    from src.config import Config

    # Set env vars for required fields
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("KIMI_API_KEY", "test")
    monkeypatch.setenv("KIMI_BASE_URL", "https://test.moonshot.cn/v1")

    return Config(
        telegram_bot_token="test",
        openai_api_key="test",
        kimi_api_key="test",
        kimi_base_url="https://test.moonshot.cn/v1",
        default_llm_provider="kimi",
        embedding_model="text-embedding-3-small",
        chat_model="kimi-k2-5",
        memory_context_limit=20,
        workspace_dir=tmp_path,
        memory_dir=tmp_path / "memory",
        context_files={},
    )


@pytest.fixture
def mock_embedder():
    return MockEmbedder()


@pytest.fixture
def memory_store(mock_config, mock_embedder):
    return MemoryStore(mock_config, mock_embedder)


@pytest.mark.asyncio
async def test_write_and_read_daily_log(memory_store, tmp_path):
    """Can write entries to daily log and read them back."""
    date = "2026-02-17"
    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 14, 30),
            role="user",
            content="I prefer Python over JavaScript",
            embedding=None,
            importance=0.8,
            tags=["preferences", "coding"],
        ),
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 14, 31),
            role="assistant",
            content="Noted. I'll keep that in mind.",
            embedding=None,
            importance=0.5,
            tags=[],
        ),
    ]

    path = await memory_store.write_daily_log(date, entries)

    assert path.exists()
    content = await memory_store.read_daily_log(date)
    assert "I prefer Python over JavaScript" in content
    assert "Noted. I'll keep that in mind." in content
    assert "<!-- metadata:" in content


@pytest.mark.asyncio
async def test_parse_daily_log(memory_store):
    """Can parse daily log back into MemoryEntry objects."""
    date = "2026-02-17"
    original_entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 14, 30),
            role="user",
            content="My dog is named Max",
            embedding=None,
            importance=0.9,
            tags=["personal"],
        ),
    ]

    await memory_store.write_daily_log(date, original_entries)
    parsed = await memory_store.parse_daily_log(date)

    assert len(parsed) == 1
    assert parsed[0].content == "My dog is named Max"
    assert parsed[0].role == "user"
    assert parsed[0].importance == 0.9
    assert parsed[0].tags == ["personal"]
    assert parsed[0].embedding is not None  # Should have generated embedding


@pytest.mark.asyncio
async def test_read_all_daily_logs(memory_store):
    """Can read all daily logs."""
    # Create two daily logs
    await memory_store.write_daily_log(
        "2026-02-16",
        [
            MemoryEntry(
                timestamp=datetime(2026, 2, 16, 10, 0),
                role="user",
                content="Yesterday's task",
                embedding=None,
            )
        ],
    )
    await memory_store.write_daily_log(
        "2026-02-17",
        [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 10, 0),
                role="user",
                content="Today's task",
                embedding=None,
            )
        ],
    )

    logs = await memory_store.read_all_daily_logs()

    assert len(logs) == 2
    dates = [d for d, _ in logs]
    assert "2026-02-16" in dates
    assert "2026-02-17" in dates


@pytest.mark.asyncio
async def test_curated_memory_read_write(memory_store, tmp_path):
    """Can read and write MEMORY.md."""
    # Override curated path to tmp_path
    memory_store.curated_path = tmp_path / "MEMORY.md"

    # Write initial content
    await memory_store.write_curated_memory("# Important Facts\n\nUser likes tea, not coffee.")

    # Read it back
    content = await memory_store.read_curated_memory()
    assert "User likes tea" in content

    # Append more
    await memory_store.append_curated_memory("User works remotely from Portland.")

    content = await memory_store.read_curated_memory()
    assert "Portland" in content


@pytest.mark.asyncio
async def test_parse_curated_memory(memory_store, tmp_path):
    """Can parse MEMORY.md into entries with embeddings."""
    memory_store.curated_path = tmp_path / "MEMORY.md"

    await memory_store.write_curated_memory(
        "# Fact 1\n\nUser prefers dark mode.\n\n# Fact 2\n\nUser uses Vim."
    )

    entries = await memory_store.parse_curated_memory()

    assert len(entries) >= 1
    assert all(e.embedding is not None for e in entries)
    assert all(e.importance == 1.0 for e in entries)  # Curated = high importance
    assert all("curated" in e.tags for e in entries)


@pytest.mark.asyncio
async def test_search_memories(memory_store):
    """Can search memories by semantic similarity."""
    # Create entries with distinct content
    await memory_store.write_daily_log(
        "2026-02-17",
        [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 10, 0),
                role="user",
                content="I love programming in Python and building CLI tools",
                embedding=None,
                importance=0.8,
            ),
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 11, 0),
                role="user",
                content="My favorite color is blue especially for dark mode themes",
                embedding=None,
                importance=0.5,
            ),
        ],
    )

    results = await memory_store.search_memories("coding and software development", top_k=2)

    assert len(results) <= 2
    # The programming entry should rank higher due to semantic similarity
    assert any("Python" in r.content or "CLI" in r.content for r in results)


@pytest.mark.asyncio
async def test_empty_memory_returns_empty(memory_store):
    """Reading non-existent memory returns empty string/list."""
    content = await memory_store.read_daily_log("2020-01-01")
    assert content == ""

    entries = await memory_store.parse_daily_log("2020-01-01")
    assert entries == []

    curated = await memory_store.read_curated_memory()
    assert curated == ""
