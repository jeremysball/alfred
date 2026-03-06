"""Tests for FAISS memory store."""

from datetime import datetime
from pathlib import Path

import pytest

from alfred.memory.faiss_store import FAISSMemoryStore


class TestFAISSMemoryStore:
    """Test FAISS-backed memory storage."""

    @pytest.fixture
    def store(self, tmp_path: Path) -> FAISSMemoryStore:
        """Create FAISSMemoryStore with mock provider."""
        from alfred.embeddings.bge_provider import BGEProvider

        provider = BGEProvider()
        index_path = tmp_path / "faiss"
        index_path.mkdir()

        return FAISSMemoryStore(
            index_path=index_path,
            provider=provider,
        )

    def test_dimension_matches_provider(self, store: FAISSMemoryStore) -> None:
        """Store dimension should match provider dimension."""
        assert store.dimension == 768  # BGE-base

    @pytest.mark.asyncio
    async def test_add_and_search(self, store: FAISSMemoryStore) -> None:
        """Should add entry and find it via search."""
        from alfred.memory import MemoryEntry

        entry = MemoryEntry(
            timestamp=datetime.now(),
            role="user",
            content="The cat sat on the mat",
            tags=["test"],
        )

        await store.add(entry)

        results, _, _ = await store.search("cat sitting", top_k=1)

        assert len(results) == 1
        assert "cat" in results[0].content.lower()

    @pytest.mark.asyncio
    async def test_search_returns_similarity_scores(self, store: FAISSMemoryStore) -> None:
        """Search should return similarity scores."""
        from alfred.memory import MemoryEntry

        entry = MemoryEntry(
            timestamp=datetime.now(),
            role="user",
            content="Python is a programming language",
            tags=[],
        )

        await store.add(entry)

        results, similarities, scores = await store.search("coding in python", top_k=1)

        assert len(results) == 1
        entry_id = results[0].entry_id
        assert entry_id in similarities
        assert similarities[entry_id] > 0.5  # Should be similar

    @pytest.mark.asyncio
    async def test_get_by_id(self, store: FAISSMemoryStore) -> None:
        """Should retrieve entry by ID."""
        from alfred.memory import MemoryEntry

        entry = MemoryEntry(
            timestamp=datetime.now(),
            role="assistant",
            content="Test content",
            tags=["tag1"],
        )

        await store.add(entry)

        retrieved = await store.get_by_id(entry.entry_id)

        assert retrieved is not None
        assert retrieved.content == "Test content"
        assert retrieved.entry_id == entry.entry_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, store: FAISSMemoryStore) -> None:
        """Should return None for non-existent ID."""
        result = await store.get_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_by_id(self, store: FAISSMemoryStore) -> None:
        """Should mark entry as deleted."""
        from alfred.memory import MemoryEntry

        entry = MemoryEntry(
            timestamp=datetime.now(),
            role="user",
            content="To be deleted",
            tags=[],
        )

        await store.add(entry)

        # Verify it exists
        retrieved = await store.get_by_id(entry.entry_id)
        assert retrieved is not None

        # Delete it
        success, msg = await store.delete_by_id(entry.entry_id)
        assert success is True

        # Should be marked deleted
        retrieved = await store.get_by_id(entry.entry_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_search_top_k_limit(self, store: FAISSMemoryStore) -> None:
        """Should respect top_k limit."""
        from alfred.memory import MemoryEntry

        for i in range(5):
            entry = MemoryEntry(
                timestamp=datetime.now(),
                role="user",
                content=f"Document number {i}",
                tags=[],
            )
            await store.add(entry)

        results, _, _ = await store.search("document", top_k=3)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_persistence_save_and_load(self, store: FAISSMemoryStore, tmp_path: Path) -> None:
        """Should persist and load index + metadata."""
        from alfred.embeddings.bge_provider import BGEProvider
        from alfred.memory import MemoryEntry

        # Add some entries
        for i in range(3):
            entry = MemoryEntry(
                timestamp=datetime.now(),
                role="user",
                content=f"Persistent content {i}",
                tags=[],
            )
            await store.add(entry)

        # Save
        await store.save()

        # Create new store instance (simulates restart)
        provider = BGEProvider()
        new_store = FAISSMemoryStore(
            index_path=tmp_path / "faiss",
            provider=provider,
        )

        # Load
        await new_store.load()

        # Should have same entries
        all_entries = await new_store.get_all_entries()
        assert len(all_entries) == 3

    @pytest.mark.asyncio
    async def test_get_all_entries(self, store: FAISSMemoryStore) -> None:
        """Should return all non-deleted entries."""
        from alfred.memory import MemoryEntry

        for i in range(3):
            entry = MemoryEntry(
                timestamp=datetime.now(),
                role="user",
                content=f"Entry {i}",
                tags=[],
            )
            await store.add(entry)

        entries = await store.get_all_entries()

        assert len(entries) == 3

    @pytest.mark.asyncio
    async def test_empty_search_returns_empty(self, store: FAISSMemoryStore) -> None:
        """Search on empty store should return empty list."""
        results, _, _ = await store.search("anything", top_k=5)

        assert results == []

    def test_auto_index_type_selection(self, tmp_path: Path) -> None:
        """Should auto-select IVF at threshold."""
        from alfred.embeddings.bge_provider import BGEProvider

        provider = BGEProvider()
        index_path = tmp_path / "faiss"
        index_path.mkdir()

        # Small store should use Flat
        store = FAISSMemoryStore(
            index_path=index_path,
            provider=provider,
            index_type="auto",
            ivf_threshold=100,  # Lower for testing
        )

        assert store._index_type == "flat"

        # After adding threshold entries, should switch to IVF
        # (This would be tested in integration test due to time)


class TestFAISSMemoryStoreConfig:
    """Test FAISS store configuration options."""

    def test_custom_index_type_flat(self, tmp_path: Path) -> None:
        """Should respect explicit flat index type."""
        from alfred.embeddings.bge_provider import BGEProvider

        provider = BGEProvider()
        index_path = tmp_path / "faiss"
        index_path.mkdir()

        store = FAISSMemoryStore(
            index_path=index_path,
            provider=provider,
            index_type="flat",
        )

        assert store._index_type == "flat"

    def test_custom_rebuild_threshold(self, tmp_path: Path) -> None:
        """Should accept custom rebuild threshold."""
        from alfred.embeddings.bge_provider import BGEProvider

        provider = BGEProvider()
        index_path = tmp_path / "faiss"
        index_path.mkdir()

        store = FAISSMemoryStore(
            index_path=index_path,
            provider=provider,
            rebuild_threshold=0.3,
        )

        assert store._rebuild_threshold == 0.3
