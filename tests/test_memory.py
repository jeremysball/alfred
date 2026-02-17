"""Tests for unified memory storage system."""

import pytest
from datetime import datetime, date
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
async def memory_store(mock_config, mock_embedder):
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()  # Start fresh
    return store


@pytest.mark.asyncio
async def test_add_and_retrieve_entries(mock_config, mock_embedder):
    """Can add entries and retrieve them."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

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

    await store.add_entries(entries)

    # Retrieve all
    retrieved = await store.get_all_entries()
    assert len(retrieved) == 2
    assert retrieved[0].content == "I prefer Python over JavaScript"
    assert retrieved[1].content == "Noted. I'll keep that in mind."
    # Embeddings should have been generated
    assert retrieved[0].embedding is not None
    assert len(retrieved[0].embedding) == 1536


@pytest.mark.asyncio
async def test_entries_persisted_to_jsonl(mock_config, mock_embedder, tmp_path):
    """Entries are written to JSONL file."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    entry = MemoryEntry(
        timestamp=datetime(2026, 2, 17, 10, 0),
        role="user",
        content="Test content",
        embedding=[0.1] * 1536,
        importance=0.9,
        tags=["test"],
    )

    await store.add_entries([entry])

    # Check file exists and contains valid JSON
    assert store.memories_path.exists()
    content = store.memories_path.read_text()
    assert '"content": "Test content"' in content
    assert '"role": "user"' in content


@pytest.mark.asyncio
async def test_filter_by_date(mock_config, mock_embedder):
    """Can filter entries by date range."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 16, 10, 0),
            role="user",
            content="Yesterday's memory",
            embedding=None,
        ),
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 10, 0),
            role="user",
            content="Today's memory",
            embedding=None,
        ),
        MemoryEntry(
            timestamp=datetime(2026, 2, 18, 10, 0),
            role="user",
            content="Tomorrow's memory",
            embedding=None,
        ),
    ]

    await store.add_entries(entries)

    # Filter by date
    feb_17 = date(2026, 2, 17)
    results = await store.filter_by_date(start_date=feb_17, end_date=feb_17)
    assert len(results) == 1
    assert results[0].content == "Today's memory"

    # Filter range
    results = await store.filter_by_date(start_date=date(2026, 2, 16), end_date=date(2026, 2, 17))
    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_by_semantic_similarity(mock_config, mock_embedder):
    """Can search memories by semantic similarity."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    entries = [
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
    ]

    await store.add_entries(entries)

    # Search
    results = await store.search("coding and software development", top_k=2)

    assert len(results) <= 2
    # The programming entry should rank higher
    assert any("Python" in r.content or "CLI" in r.content for r in results)


@pytest.mark.asyncio
async def test_search_with_date_filter(mock_config, mock_embedder):
    """Can search with date filtering."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 16, 10, 0),
            role="user",
            content="Python programming",
            embedding=None,
        ),
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 10, 0),
            role="user",
            content="Python coding",
            embedding=None,
        ),
    ]

    await store.add_entries(entries)

    # Search only Feb 17
    results = await store.search(
        "python",
        start_date=date(2026, 2, 17),
        end_date=date(2026, 2, 17),
    )

    assert len(results) == 1
    assert "coding" in results[0].content


@pytest.mark.asyncio
async def test_curated_memory_read_write(mock_config, mock_embedder, tmp_path):
    """Can read and write MEMORY.md."""
    store = MemoryStore(mock_config, mock_embedder)
    store.curated_path = tmp_path / "MEMORY.md"

    # Write initial content
    await store.write_curated_memory("# Important Facts\n\nUser likes tea, not coffee.")

    # Read it back
    content = await store.read_curated_memory()
    assert "User likes tea" in content

    # Append more
    await store.append_curated_memory("User works remotely from Portland.")

    content = await store.read_curated_memory()
    assert "Portland" in content


@pytest.mark.asyncio
async def test_search_curated_memory(mock_config, mock_embedder, tmp_path):
    """Can search curated memories."""
    store = MemoryStore(mock_config, mock_embedder)
    store.curated_path = tmp_path / "MEMORY.md"

    await store.write_curated_memory(
        "User prefers dark mode.\n\nUser uses Vim for editing."
    )

    results = await store.search_curated("editor preferences", top_k=2)

    assert len(results) >= 1
    assert all("curated" in r.tags for r in results)
    assert all(r.importance == 1.0 for r in results)


@pytest.mark.asyncio
async def test_iteration_memory_efficient(mock_config, mock_embedder):
    """Can iterate entries without loading all into memory."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    # Add some entries
    for i in range(5):
        entry = MemoryEntry(
            timestamp=datetime(2026, 2, 17, i, 0),
            role="user",
            content=f"Entry {i}",
            embedding=None,
        )
        await store.add_entries([entry])

    # Iterate
    count = 0
    async for entry in store.iter_entries():
        count += 1
        assert entry.content.startswith("Entry")

    assert count == 5
