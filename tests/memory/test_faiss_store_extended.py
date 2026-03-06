"""Extended tests for FAISS memory store covering new M3 methods."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.memory.faiss_store import FAISSMemoryStore
from src.memory.faiss_store import MemoryEntry


@pytest.fixture
def store(tmp_path: Path) -> FAISSMemoryStore:
    from src.embeddings.bge_provider import BGEProvider
    provider = BGEProvider()
    index_path = tmp_path / "faiss"
    index_path.mkdir()
    return FAISSMemoryStore(index_path=index_path, provider=provider)

@pytest.mark.asyncio
async def test_add_entries_batch(store: FAISSMemoryStore) -> None:
    """Should add multiple entries efficiently."""
    entries = [
        MemoryEntry(content="Batch 1", role="user"),
        MemoryEntry(content="Batch 2", role="user"),
        MemoryEntry(content="Batch 3", role="user"),
    ]
    await store.add_entries(entries)
    all_entries = await store.get_all_entries()
    assert len(all_entries) == 3

@pytest.mark.asyncio
async def test_prune_expired_memories(store: FAISSMemoryStore) -> None:
    """Should remove non-permanent memories older than TTL."""
    old_time = datetime.now() - timedelta(days=100)
    entries = [
        MemoryEntry(content="Old normal", role="user", timestamp=old_time),
        MemoryEntry(content="Old perm", role="user", timestamp=old_time, permanent=True),
        MemoryEntry(content="New normal", role="user", timestamp=datetime.now()),
    ]
    await store.add_entries(entries)
    
    # Dry run
    pruned = await store.prune_expired_memories(ttl_days=90, dry_run=True)
    assert pruned == 1
    assert len(await store.get_all_entries()) == 3
    
    # Actual prune
    pruned = await store.prune_expired_memories(ttl_days=90, dry_run=False)
    assert pruned == 1
    
    all_entries = await store.get_all_entries()
    assert len(all_entries) == 2
    contents = [e.content for e in all_entries]
    assert "Old normal" not in contents

@pytest.mark.asyncio
async def test_update_entry(store: FAISSMemoryStore) -> None:
    """Should update content and regenerate embedding."""
    entry = MemoryEntry(content="Original content", role="user")
    await store.add(entry)
    
    success, msg = await store.update_entry(entry.entry_id, new_content="Updated content")
    assert success is True
    
    updated = await store.get_by_id(entry.entry_id)
    assert updated is not None
    assert updated.content == "Updated content"

def test_check_memory_threshold(store: FAISSMemoryStore) -> None:
    """Should report if threshold is exceeded."""
    import asyncio
    entry = MemoryEntry(content="Test", role="user")
    asyncio.run(store.add(entry))
    
    exceeded, count = store.check_memory_threshold(threshold=0)
    assert exceeded is True
    assert count == 1
    
    exceeded, count = store.check_memory_threshold(threshold=10)
    assert exceeded is False
    assert count == 1
