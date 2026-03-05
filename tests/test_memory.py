"""Tests for unified memory storage system."""

from datetime import date, datetime, timedelta

import pytest

from src.memory.jsonl_store import JSONLMemoryStore as MemoryStore
from src.memory.jsonl_store import MemoryEntry


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
    store = MemoryStore(config=mock_config, embedder=mock_embedder)
    await store.clear()  # Start fresh
    return store


@pytest.mark.asyncio
async def test_add_and_retrieve_entries(mock_config, mock_embedder):
    """Can add entries and retrieve them."""
    store = MemoryStore(config=mock_config, embedder=mock_embedder)
    await store.clear()

    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 14, 30),
            role="user",
            content="I prefer Python over JavaScript",
            embedding=None,
            tags=["preferences", "coding"],
        ),
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 14, 31),
            role="assistant",
            content="Noted. I'll keep that in mind.",
            embedding=None,
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
    store = MemoryStore(config=mock_config, embedder=mock_embedder)
    await store.clear()

    entry = MemoryEntry(
        timestamp=datetime(2026, 2, 17, 10, 0),
        role="user",
        content="Test content",
        embedding=[0.1] * 1536,
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
    store = MemoryStore(config=mock_config, embedder=mock_embedder)
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
    store = MemoryStore(config=mock_config, embedder=mock_embedder)
    await store.clear()

    entries = [
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 10, 0),
            role="user",
            content="I love programming in Python and building CLI tools",
            embedding=None,
        ),
        MemoryEntry(
            timestamp=datetime(2026, 2, 17, 11, 0),
            role="user",
            content="My favorite color is blue especially for dark mode themes",
            embedding=None,
        ),
    ]

    await store.add_entries(entries)

    # Search
    results, _, _ = await store.search("coding and software development", top_k=2)

    assert len(results) <= 2
    # The programming entry should rank higher
    assert any("Python" in r.content or "CLI" in r.content for r in results)


@pytest.mark.asyncio
async def test_search_with_date_filter(mock_config, mock_embedder):
    """Can search with date filtering."""
    store = MemoryStore(config=mock_config, embedder=mock_embedder)
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
    results, _, _ = await store.search(
        "python",
        start_date=date(2026, 2, 17),
        end_date=date(2026, 2, 17),
    )

    assert len(results) == 1
    assert "coding" in results[0].content


@pytest.mark.asyncio
async def test_iteration_memory_efficient(mock_config, mock_embedder):
    """Can iterate entries without loading all into memory."""
    store = MemoryStore(config=mock_config, embedder=mock_embedder)
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


class TestMemoryStoreErrorHandling:
    """Test fail-fast behavior when embedding fails."""

    @pytest.mark.asyncio
    async def test_add_entries_fails_fast_on_embedding_error(self, mock_config, tmp_path):
        """If embedding fails, no entries are written (fail fast)."""
        from src.embeddings.openai_provider import EmbeddingError

        class FailingEmbedder:
            async def embed(self, text: str) -> list[float]:
                raise EmbeddingError("API failure")

            async def embed_batch(self, texts: list[str]) -> list[list[float]]:
                raise EmbeddingError("API failure")

        store = MemoryStore(config=mock_config, embedder=FailingEmbedder())
        await store.clear()

        entries = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 10, 0),
                role="user",
                content="Should not be written",
                embedding=None,
            )
        ]

        with pytest.raises(EmbeddingError):
            await store.add_entries(entries)

        # Verify nothing was written
        retrieved = await store.get_all_entries()
        assert len(retrieved) == 0

    @pytest.mark.asyncio
    async def test_add_entries_fails_fast_on_partial_embeddings(self, mock_config):
        """If some entries lack embeddings after embedding call, fail fast."""

        class PartialEmbedder:
            """Returns fewer embeddings than requested."""

            async def embed(self, text: str) -> list[float]:
                return [0.1] * 1536

            async def embed_batch(self, texts: list[str]) -> list[list[float]]:
                # Return fewer embeddings than requested (simulating API bug)
                return [[0.1] * 1536] * (len(texts) - 1)

        store = MemoryStore(config=mock_config, embedder=PartialEmbedder())
        await store.clear()

        entries = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 10, 0),
                role="user",
                content="Entry 1",
                embedding=None,
            ),
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 10, 1),
                role="user",
                content="Entry 2",
                embedding=None,
            ),
        ]

        # Should fail because entry 2 won't get an embedding
        with pytest.raises(ValueError) as exc_info:
            await store.add_entries(entries)

        assert "without embeddings" in str(exc_info.value)

        # Verify nothing was written
        retrieved = await store.get_all_entries()
        assert len(retrieved) == 0

    @pytest.mark.asyncio
    async def test_add_entries_with_pre_existing_embeddings(self, mock_config):
        """Entries with pre-existing embeddings are written successfully."""
        store = MemoryStore(config=mock_config, embedder=MockEmbedder())
        await store.clear()

        entries = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 10, 0),
                role="user",
                content="Already embedded",
                embedding=[0.5] * 1536,  # Pre-existing embedding
            )
        ]

        await store.add_entries(entries)

        retrieved = await store.get_all_entries()
        assert len(retrieved) == 1
        assert retrieved[0].content == "Already embedded"
        assert retrieved[0].embedding == [0.5] * 1536

    @pytest.mark.asyncio
    async def test_add_entries_mixed_embeddings(self, mock_config):
        """Mix of pre-embedded and new entries works correctly."""
        store = MemoryStore(config=mock_config, embedder=MockEmbedder())
        await store.clear()

        entries = [
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 10, 0),
                role="user",
                content="Pre-embedded",
                embedding=[0.5] * 1536,
            ),
            MemoryEntry(
                timestamp=datetime(2026, 2, 17, 10, 1),
                role="user",
                content="Needs embedding",
                embedding=None,
            ),
        ]

        await store.add_entries(entries)

        retrieved = await store.get_all_entries()
        assert len(retrieved) == 2
        # First entry keeps original embedding
        assert retrieved[0].embedding == [0.5] * 1536
        # Second entry got embedded
        assert retrieved[1].embedding is not None
        assert len(retrieved[1].embedding) == 1536


# Tests for permanent flag
class TestMemoryEntryPermanentFlag:
    """Test permanent flag on MemoryEntry."""

    def test_memory_entry_has_permanent_field(self):
        """MemoryEntry has permanent field."""
        entry = MemoryEntry(
            timestamp=datetime(2026, 3, 4, 10, 0),
            role="user",
            content="Test memory",
        )
        assert hasattr(entry, "permanent")

    def test_memory_entry_permanent_defaults_to_false(self):
        """MemoryEntry permanent field defaults to False."""
        entry = MemoryEntry(
            timestamp=datetime(2026, 3, 4, 10, 0),
            role="user",
            content="Test memory",
        )
        assert entry.permanent is False

    def test_memory_entry_permanent_can_be_set_true(self):
        """MemoryEntry permanent can be set to True."""
        entry = MemoryEntry(
            timestamp=datetime(2026, 3, 4, 10, 0),
            role="user",
            content="Important memory",
            permanent=True,
        )
        assert entry.permanent is True


# Tests for memory count
class TestMemoryStoreCount:
    """Test memory count functionality."""

    @pytest.mark.asyncio
    async def test_get_memory_count_empty_store(self, mock_config, mock_embedder):
        """get_memory_count returns 0 when store is empty."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        count = await store.get_memory_count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_memory_count_with_entries(self, mock_config, mock_embedder):
        """get_memory_count returns correct count after adding entries."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        entries = [
            MemoryEntry(
                timestamp=datetime(2026, 3, 4, 10, 0),
                role="user",
                content="First memory",
            ),
            MemoryEntry(
                timestamp=datetime(2026, 3, 4, 10, 1),
                role="user",
                content="Second memory",
            ),
            MemoryEntry(
                timestamp=datetime(2026, 3, 4, 10, 2),
                role="user",
                content="Third memory",
            ),
        ]

        await store.add_entries(entries)
        count = await store.get_memory_count()
        assert count == 3


# Tests for permanent flag serialization
class TestMemoryEntrySerialization:
    """Test permanent flag is serialized/deserialized correctly."""

    @pytest.mark.asyncio
    async def test_entry_to_jsonl_includes_permanent(self, mock_config, mock_embedder):
        """Serialization includes permanent field."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        entry = MemoryEntry(
            timestamp=datetime(2026, 3, 4, 10, 0),
            role="user",
            content="Important memory",
            permanent=True,
        )

        jsonl_line = store._entry_to_jsonl(entry)
        assert '"permanent": true' in jsonl_line

    @pytest.mark.asyncio
    async def test_entry_from_jsonl_parses_permanent(self, mock_config, mock_embedder):
        """Deserialization parses permanent field."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)

        # Create JSONL line with permanent=True
        jsonl_line = '{"timestamp": "2026-03-04T10:00:00", "role": "user", "content": "Important", "embedding": null, "tags": [], "entry_id": "test123", "permanent": true}'

        entry = store._entry_from_jsonl(jsonl_line)
        assert entry.permanent is True

    @pytest.mark.asyncio
    async def test_entry_from_jsonl_backward_compatible(self, mock_config, mock_embedder):
        """Old data without permanent field defaults to False."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)

        # Create JSONL line without permanent field (old format)
        jsonl_line = '{"timestamp": "2026-03-04T10:00:00", "role": "user", "content": "Old memory", "embedding": null, "tags": [], "entry_id": "test456"}'

        entry = store._entry_from_jsonl(jsonl_line)
        assert entry.permanent is False


# Tests for TTL pruning
class TestMemoryStoreTTLPruning:
    """Test TTL-based memory pruning."""

    @pytest.mark.asyncio
    async def test_prune_expired_memories_removes_old_non_permanent(self, mock_config, mock_embedder):
        """Pruning removes non-permanent memories older than TTL."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        # Create old non-permanent memory (91 days ago)
        old_date = datetime.now() - timedelta(days=91)
        old_entry = MemoryEntry(
            timestamp=old_date,
            role="user",
            content="Old memory to prune",
            permanent=False,
        )

        # Create recent memory
        recent_entry = MemoryEntry(
            timestamp=datetime.now(),
            role="user",
            content="Recent memory to keep",
            permanent=False,
        )

        await store.add_entries([old_entry, recent_entry])

        # Prune with 90-day TTL
        pruned_count = await store.prune_expired_memories(ttl_days=90, dry_run=False)

        assert pruned_count == 1

        # Verify old memory removed, recent kept
        remaining = await store.get_all_entries()
        assert len(remaining) == 1
        assert remaining[0].content == "Recent memory to keep"

    @pytest.mark.asyncio
    async def test_prune_expired_memories_keeps_permanent(self, mock_config, mock_embedder):
        """Pruning never removes permanent memories."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        # Create old permanent memory (91 days ago)
        old_date = datetime.now() - timedelta(days=91)
        old_permanent = MemoryEntry(
            timestamp=old_date,
            role="user",
            content="Old permanent memory",
            permanent=True,
        )

        await store.add_entries([old_permanent])

        # Prune with 90-day TTL
        pruned_count = await store.prune_expired_memories(ttl_days=90, dry_run=False)

        assert pruned_count == 0

        # Verify permanent memory kept
        remaining = await store.get_all_entries()
        assert len(remaining) == 1
        assert remaining[0].content == "Old permanent memory"

    @pytest.mark.asyncio
    async def test_prune_expired_memories_keeps_recent(self, mock_config, mock_embedder):
        """Pruning keeps memories newer than TTL."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        # Create memory exactly 89 days old
        recent_date = datetime.now() - timedelta(days=89)
        recent_entry = MemoryEntry(
            timestamp=recent_date,
            role="user",
            content="Memory under TTL",
            permanent=False,
        )

        await store.add_entries([recent_entry])

        # Prune with 90-day TTL
        pruned_count = await store.prune_expired_memories(ttl_days=90, dry_run=False)

        assert pruned_count == 0

        # Verify memory kept
        remaining = await store.get_all_entries()
        assert len(remaining) == 1

    @pytest.mark.asyncio
    async def test_prune_expired_memories_dry_run(self, mock_config, mock_embedder):
        """Dry run returns count without deleting."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        # Create old memory (91 days ago)
        old_date = datetime.now() - timedelta(days=91)
        old_entry = MemoryEntry(
            timestamp=old_date,
            role="user",
            content="Old memory",
            permanent=False,
        )

        await store.add_entries([old_entry])

        # Dry run
        pruned_count = await store.prune_expired_memories(ttl_days=90, dry_run=True)

        assert pruned_count == 1

        # Verify memory NOT deleted
        remaining = await store.get_all_entries()
        assert len(remaining) == 1

    @pytest.mark.asyncio
    async def test_prune_expired_memories_boundary(self, mock_config, mock_embedder):
        """Memory exactly 90 days old is kept (end-of-day boundary)."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        # Create memory exactly 90 days old
        boundary_date = datetime.now() - timedelta(days=90)
        boundary_entry = MemoryEntry(
            timestamp=boundary_date,
            role="user",
            content="Exactly 90 days old",
            permanent=False,
        )

        await store.add_entries([boundary_entry])

        # Prune with 90-day TTL
        pruned_count = await store.prune_expired_memories(ttl_days=90, dry_run=False)

        assert pruned_count == 0

        # Verify memory kept (end of day 90)
        remaining = await store.get_all_entries()
        assert len(remaining) == 1


# Tests for threshold checking
class TestMemoryStoreThreshold:
    """Test memory threshold checking."""

    @pytest.mark.asyncio
    async def test_check_memory_threshold_below_threshold(self, mock_config, mock_embedder):
        """Returns False when count below threshold."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        # Add 5 memories
        for i in range(5):
            entry = MemoryEntry(
                timestamp=datetime.now(),
                role="user",
                content=f"Memory {i}",
            )
            await store.add_entries([entry])

        exceeded, count = store.check_memory_threshold(threshold=10)
        assert exceeded is False
        assert count == 5

    @pytest.mark.asyncio
    async def test_check_memory_threshold_at_threshold(self, mock_config, mock_embedder):
        """Returns False when count equals threshold (only exceeds triggers warning)."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        # Add exactly 10 memories
        for i in range(10):
            entry = MemoryEntry(
                timestamp=datetime.now(),
                role="user",
                content=f"Memory {i}",
            )
            await store.add_entries([entry])

        exceeded, count = store.check_memory_threshold(threshold=10)
        assert exceeded is False
        assert count == 10

    @pytest.mark.asyncio
    async def test_check_memory_threshold_above_threshold(self, mock_config, mock_embedder):
        """Returns True when count exceeds threshold."""
        store = MemoryStore(config=mock_config, embedder=mock_embedder)
        await store.clear()

        # Add 15 memories
        for i in range(15):
            entry = MemoryEntry(
                timestamp=datetime.now(),
                role="user",
                content=f"Memory {i}",
            )
            await store.add_entries([entry])

        exceeded, count = store.check_memory_threshold(threshold=10)
        assert exceeded is True
        assert count == 15
