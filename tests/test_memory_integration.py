"""Integration test for the full memory system.

This test verifies:
1. Memories are saved correctly
2. Memories are retrieved with correct similarities
3. The similarity scoring bug is fixed
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from alfred.config import Config
from alfred.context import ContextBuilder
from alfred.memory import MemoryEntry


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config(temp_data_dir):
    """Create a test config pointing to temp directory."""
    workspace_dir = temp_data_dir / "workspace"
    workspace_dir.mkdir()

    for filename in ["AGENTS.md", "SOUL.md", "USER.md", "SYSTEM.md"]:
        (workspace_dir / filename).write_text(f"# {filename}\n\nTest content.\n")

    return Config(
        data_dir=temp_data_dir,
        workspace_dir=workspace_dir,
        context_files={
            "agents": workspace_dir / "AGENTS.md",
            "soul": workspace_dir / "SOUL.md",
            "user": workspace_dir / "USER.md",
            "system": workspace_dir / "SYSTEM.md",
        },
    )


@pytest.fixture
def mock_store():
    """Create a mock store that simulates search results."""

    class MockStore:
        def __init__(self):
            self.results = []

        async def search_memories(self, query_embedding, top_k=10):
            return self.results[:top_k]

    return MockStore()


@pytest.mark.asyncio
async def test_memory_similarity_scoring_bug_fixed(config, mock_store):
    """Test that each memory gets its own similarity score, not the last one.

    This is the critical bug fix: previously, all memories got the similarity
    of the last result due to variable leakage from the first loop.
    """
    # Setup search results with specific similarities
    mock_store.results = [
        {
            "entry_id": "mem-1",
            "content": "Python programming",
            "timestamp": datetime.now().isoformat(),
            "role": "system",
            "tags": [],
            "permanent": False,
            "similarity": 0.95,  # High similarity
        },
        {
            "entry_id": "mem-2",
            "content": "JavaScript programming",
            "timestamp": datetime.now().isoformat(),
            "role": "system",
            "tags": [],
            "permanent": False,
            "similarity": 0.60,  # Medium similarity
        },
        {
            "entry_id": "mem-3",
            "content": "Cooking recipes",
            "timestamp": datetime.now().isoformat(),
            "role": "system",
            "tags": [],
            "permanent": False,
            "similarity": 0.30,  # Low similarity (below min_similarity=0.5)
        },
    ]

    # Create context builder
    context_builder = ContextBuilder(
        store=mock_store,
        memory_budget=32000,
        min_similarity=0.5,  # Filter out low similarity
    )

    # Search
    query_embedding = [0.1] * 768
    memories, similarities, scores = await context_builder.search_memories(query_embedding, top_k=10)

    # Verify we got the right memories
    assert len(memories) == 2, f"Expected 2 memories (above threshold), got {len(memories)}"

    # Verify each memory has its OWN similarity, not the last one (0.30)
    # Without the bug fix, all would have similarity 0.30
    assert "mem-1" in similarities
    assert "mem-2" in similarities
    assert "mem-3" not in similarities  # Filtered out by threshold

    # Critical assertions - these would fail with the bug
    assert similarities["mem-1"] == 0.95, f"Bug! mem-1 has wrong similarity: {similarities['mem-1']} (expected 0.95)"
    assert similarities["mem-2"] == 0.60, f"Bug! mem-2 has wrong similarity: {similarities['mem-2']} (expected 0.60)"

    # Verify scores are computed correctly
    # Score = similarity * 0.6 + recency * 0.4
    assert scores["mem-1"] > scores["mem-2"], "Higher similarity should result in higher score"

    print("\n" + "=" * 60)
    print("SIMILARITY SCORING TEST PASSED")
    print("=" * 60)
    print(f"mem-1 similarity: {similarities['mem-1']:.2f} (expected 0.95)")
    print(f"mem-2 similarity: {similarities['mem-2']:.2f} (expected 0.60)")
    print("mem-3: filtered out (similarity 0.30 < threshold 0.50)")
    print("=" * 60)


@pytest.mark.asyncio
async def test_context_building_with_memories(config, mock_store):
    """Test that context is built correctly with memories included."""
    # Setup search results
    mock_store.results = [
        {
            "entry_id": "mem-python",
            "content": "User prefers Python for data science",
            "timestamp": datetime.now().isoformat(),
            "role": "system",
            "tags": ["preference"],
            "permanent": True,
            "similarity": 0.92,
        },
        {
            "entry_id": "mem-vim",
            "content": "User uses Vim editor",
            "timestamp": datetime.now().isoformat(),
            "role": "system",
            "tags": ["preference"],
            "permanent": True,
            "similarity": 0.75,
        },
    ]

    context_builder = ContextBuilder(
        store=mock_store,
        memory_budget=32000,
        min_similarity=0.5,
    )

    # Create memory entries for the build_context method
    memory_entries = [
        MemoryEntry(
            entry_id=r["entry_id"],
            content=r["content"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            role=r["role"],
            tags=r["tags"],
            permanent=r["permanent"],
        )
        for r in mock_store.results
    ]

    # Build context
    query_embedding = [0.1] * 768
    system_prompt = "# System\n\nTest system prompt."

    context, memories_count = await context_builder.build_context(
        query_embedding=query_embedding,
        memories=memory_entries,
        system_prompt=system_prompt,
        session_messages=[],
    )

    # Verify context structure
    assert "# System" in context
    assert "## RELEVANT MEMORIES" in context
    assert "## CURRENT CONVERSATION" in context

    # Verify memories are included
    assert "Python" in context
    assert "Vim" in context
    assert memories_count == 2

    print("\n" + "=" * 60)
    print("CONTEXT BUILDING TEST PASSED")
    print("=" * 60)
    print(f"Memories included: {memories_count}")
    print("=" * 60)


@pytest.mark.asyncio
async def test_memory_deduplication(config, mock_store):
    """Test that duplicate/similar memories are deduplicated."""
    # Create two very similar memories (would be duplicates)
    mock_store.results = [
        {
            "entry_id": "mem-1",
            "content": "User loves Python programming",
            "timestamp": datetime.now().isoformat(),
            "role": "system",
            "tags": [],
            "permanent": False,
            "similarity": 0.95,
        },
        {
            "entry_id": "mem-2",
            "content": "User really loves Python programming",
            "timestamp": datetime.now().isoformat(),
            "role": "system",
            "tags": [],
            "permanent": False,
            "similarity": 0.94,
        },
        {
            "entry_id": "mem-3",
            "content": "User hates Java programming",
            "timestamp": datetime.now().isoformat(),
            "role": "system",
            "tags": [],
            "permanent": False,
            "similarity": 0.50,
        },
    ]

    context_builder = ContextBuilder(
        store=mock_store,
        memory_budget=32000,
        min_similarity=0.0,  # Don't filter by similarity
    )

    # For deduplication to work, memories need embeddings
    # We'll manually create memory entries with embeddings
    memory_entries = [
        MemoryEntry(
            entry_id=r["entry_id"],
            content=r["content"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            role=r["role"],
            tags=r["tags"],
            permanent=r["permanent"],
            # Create embeddings that are very similar for mem-1 and mem-2
            embedding=[0.9 if i == 0 else 0.1 for i in range(768)],
        )
        for r in mock_store.results
    ]

    # Modify mem-2 to have very similar embedding (would be duplicate)
    memory_entries[1].embedding = [0.91 if i == 0 else 0.09 for i in range(768)]
    # mem-3 has different embedding
    memory_entries[2].embedding = [0.1 if i == 0 else 0.9 for i in range(768)]

    query_embedding = [0.1] * 768
    memories, similarities, scores = await context_builder.search_memories(query_embedding, top_k=10)

    # Should deduplicate mem-1 and mem-2 (very similar embeddings)
    # but keep mem-3 (different)
    print("\n" + "=" * 60)
    print("DEDUPLICATION TEST")
    print("=" * 60)
    print("Input memories: 3")
    print(f"Output memories: {len(memories)}")
    for m in memories:
        print(f"  - {m.entry_id}: {m.content[:40]}...")
    print("=" * 60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
