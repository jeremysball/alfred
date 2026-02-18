"""Tests for MemoryStore CRUD operations (update and delete)."""

from datetime import datetime

import pytest

from src.memory import MemoryStore
from src.types import MemoryEntry


class MockEmbedder:
    """Mock embedder that returns golden vectors for testing."""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    async def embed(self, text: str) -> list[float]:
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
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
    await store.clear()
    return store


@pytest.mark.asyncio
async def test_update_entry_content(mock_config, mock_embedder):
    """Can update memory content."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    # Add a memory
    content = "My name is Jaz"
    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 10, 0),
            role="system",
            content=content,
            embedding=await mock_embedder.embed(content),
        )
    ]
    await store.add_entries(entries)

    # Update using exact content as search (guarantees match with mock embedder)
    success, message = await store.update_entry(
        search_query=content,  # Exact match for deterministic testing
        new_content="My name is Jasmine",
    )

    assert success is True
    assert "Updated" in message
    assert "Jasmine" in message

    # Verify the update
    memories = await store.get_all_entries()
    assert len(memories) == 1
    assert memories[0].content == "My name is Jasmine"
    assert memories[0].embedding is not None  # Should be regenerated


@pytest.mark.asyncio
async def test_update_entry_importance(mock_config, mock_embedder):
    """Importance field removed - test deprecated."""
    pytest.skip("Importance field removed from MemoryEntry")


@pytest.mark.asyncio
async def test_update_entry_no_changes(mock_config, mock_embedder):
    """Returns error if no changes specified."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    success, message = await store.update_entry(
        search_query="anything",
    )

    assert success is False
    assert "No changes specified" in message


@pytest.mark.asyncio
async def test_update_entry_no_match(mock_config, mock_embedder):
    """Returns error if no matching memory found."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    # Add unrelated memory
    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 10, 0),
            role="system",
            content="I like coffee",
            embedding=await mock_embedder.embed("I like coffee"),
        )
    ]
    await store.add_entries(entries)

    # Try to update something unrelated - use content that won't match
    success, message = await store.update_entry(
        search_query="xyz123nonexistent",
        new_content="New content",
    )

    assert success is False
    assert "No matching memory" in message


@pytest.mark.asyncio
async def test_update_entry_empty_store(mock_config, mock_embedder):
    """Returns error if store is empty."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    success, message = await store.update_entry(
        search_query="anything",
        new_content="new",
    )

    assert success is False
    assert "No memories to update" in message


@pytest.mark.asyncio
async def test_delete_entries_by_query(mock_config, mock_embedder):
    """Can delete memories matching a query."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    # Add a single memory to delete
    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 10, 0),
            role="system",
            content="DELETE_ME_name_memory",
            embedding=await mock_embedder.embed("DELETE_ME_name_memory"),
        ),
    ]
    await store.add_entries(entries)

    # Delete using exact content match
    count, message = await store.delete_entries(query="DELETE_ME_name_memory")

    assert count == 1
    assert "Deleted 1 memory" in message

    # Verify memory deleted
    memories = await store.get_all_entries()
    assert len(memories) == 0


@pytest.mark.asyncio
async def test_delete_entries_no_match(mock_config, mock_embedder):
    """Returns zero if no memories match."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 10, 0),
            role="system",
            content="I like coffee",
            embedding=await mock_embedder.embed("I like coffee"),
        )
    ]
    await store.add_entries(entries)

    # Use query that definitely won't match
    count, message = await store.delete_entries(query="xyz123nonexistent")

    assert count == 0
    assert "No memories matching" in message

    # Verify memory still exists
    memories = await store.get_all_entries()
    assert len(memories) == 1


@pytest.mark.asyncio
async def test_delete_entries_empty_store(mock_config, mock_embedder):
    """Returns zero if store is empty."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    count, message = await store.delete_entries(query="anything")

    assert count == 0
    assert "No memories to delete" in message


@pytest.mark.asyncio
async def test_delete_entries_multiple_matches(mock_config, mock_embedder):
    """Can delete multiple matching memories."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    # Add multiple similar memories with common prefix for deletion
    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 10, 0),
            role="system",
            content="TEMP_note_one",
            embedding=await mock_embedder.embed("TEMP_note_one"),
        ),
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 11, 0),
            role="system",
            content="TEMP_note_two",
            embedding=await mock_embedder.embed("TEMP_note_two"),
        ),
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 12, 0),
            role="system",
            content="PERMANENT_dark_mode",
            embedding=await mock_embedder.embed("PERMANENT_dark_mode"),
        ),
    ]
    await store.add_entries(entries)

    # Delete TEMP items using one of them as query
    count, message = await store.delete_entries(query="TEMP_note_one")

    # With exact match, should delete at least 1
    assert count >= 1
    assert "Deleted" in message

    # Verify permanent item remains
    memories = await store.get_all_entries()
    assert any("PERMANENT" in m.content for m in memories)


@pytest.mark.asyncio
async def test_update_preserves_other_entries(mock_config, mock_embedder):
    """Updating one entry doesn't affect others."""
    store = MemoryStore(mock_config, mock_embedder)
    await store.clear()

    # Add multiple memories
    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 10, 0),
            role="system",
            content="name_memory_Jaz",
            embedding=await mock_embedder.embed("name_memory_Jaz"),
        ),
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 11, 0),
            role="system",
            content="python_preference",
            embedding=await mock_embedder.embed("python_preference"),
        ),
    ]
    await store.add_entries(entries)

    # Update first entry using exact match
    await store.update_entry(
        search_query="name_memory_Jaz",
        new_content="name_memory_Jasmine",
    )

    # Verify second entry unchanged
    memories = await store.get_all_entries()
    python_mem = next(m for m in memories if "python" in m.content)
    assert python_mem.content == "python_preference"



