"""Test for the memory similarity scoring bug fix.

Bug: In context.py search_memories(), the variable `r` from the previous loop
was being used to get similarity, causing all memories to get the similarity
of the LAST result instead of their own.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_store():
    """Create a mock SQLiteStore."""
    return Mock()


@pytest.fixture
def context_builder(mock_store):
    """Create a ContextBuilder with mock store."""
    from alfred.context import ContextBuilder

    return ContextBuilder(store=mock_store, memory_budget=32000, min_similarity=0.5)


@pytest.mark.asyncio
async def test_each_memory_gets_own_similarity(context_builder, mock_store):
    """Verify each memory gets its own similarity score, not the last one."""
    # Setup search results with different similarities
    mock_results = [
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

    mock_store.search_memories = AsyncMock(return_value=mock_results)

    # Search with a query embedding
    query_embedding = [0.1] * 768
    memories, similarities, scores = await context_builder.search_memories(query_embedding, top_k=10)

    # Verify each memory has its correct similarity
    assert "mem-1" in similarities
    assert "mem-2" in similarities
    # mem-3 should be filtered out due to low similarity (0.3 < 0.5)
    assert "mem-3" not in similarities

    # Check the actual similarity values
    assert similarities["mem-1"] == 0.95
    assert similarities["mem-2"] == 0.60

    # Verify scores are computed (hybrid score = similarity * 0.6 + recency * 0.4)
    # Since all memories are recent, scores should be close to similarity * 0.6 + ~0.4
    assert scores["mem-1"] > scores["mem-2"]  # Higher similarity = higher score


@pytest.mark.asyncio
async def test_memory_order_preserved(context_builder, mock_store):
    """Verify memories are sorted by hybrid score, not by original order."""
    # Setup search results with similarities that should reorder
    mock_results = [
        {
            "entry_id": "mem-low",
            "content": "Low relevance content",
            "timestamp": datetime(2026, 1, 1).isoformat(),  # Old
            "role": "system",
            "tags": [],
            "permanent": False,
            "similarity": 0.80,  # High similarity but old
        },
        {
            "entry_id": "mem-high",
            "content": "High relevance content",
            "timestamp": datetime.now().isoformat(),  # Recent
            "role": "system",
            "tags": [],
            "permanent": False,
            "similarity": 0.85,  # Higher similarity AND recent
        },
    ]

    mock_store.search_memories = AsyncMock(return_value=mock_results)

    query_embedding = [0.1] * 768
    memories, similarities, scores = await context_builder.search_memories(query_embedding, top_k=10)

    # mem-high should have higher score due to better similarity + recency
    assert scores["mem-high"] > scores["mem-low"]

    # Memories should be sorted by score descending
    assert memories[0].entry_id == "mem-high"
    assert memories[1].entry_id == "mem-low"


@pytest.mark.asyncio
async def test_no_variable_leakage_bug(context_builder, mock_store):
    """Regression test: ensure no variable leakage from result parsing loop."""
    # This test specifically checks that we don't have the bug where
    # the loop variable `r` from the first loop leaks into the second loop

    mock_results = [
        {
            "entry_id": f"mem-{i}",
            "content": f"Content {i}",
            "timestamp": datetime.now().isoformat(),
            "role": "system",
            "tags": [],
            "permanent": False,
            "similarity": float(i) / 10,  # 0.0, 0.1, 0.2, ..., 0.9
        }
        for i in range(10)
    ]

    mock_store.search_memories = AsyncMock(return_value=mock_results)

    query_embedding = [0.1] * 768
    memories, similarities, scores = await context_builder.search_memories(query_embedding, top_k=10)

    # Without the bug fix, all similarities would be 0.9 (the last value)
    # With the fix, each memory should have its own similarity
    for i in range(5, 10):  # Check memories with similarity >= 0.5
        mem_id = f"mem-{i}"
        if mem_id in similarities:
            expected_similarity = float(i) / 10
            assert similarities[mem_id] == expected_similarity, (
                f"Memory {mem_id} has wrong similarity: "
                f"expected {expected_similarity}, got {similarities[mem_id]}. "
                "Bug: variable leakage from first loop!"
            )


@pytest.mark.asyncio
async def test_context_builder_min_similarity_accepts_best_memory_match_after_normalization():
    """The best semantic match should survive the similarity threshold."""

    class MockStore:
        async def search_memories(self, query_embedding, top_k=10):
            return [
                {
                    "entry_id": "mem-close",
                    "content": "Best semantic match",
                    "timestamp": datetime.now().isoformat(),
                    "role": "system",
                    "tags": [],
                    "permanent": False,
                    "similarity": 0.95,
                },
                {
                    "entry_id": "mem-far",
                    "content": "Worse semantic match",
                    "timestamp": datetime.now().isoformat(),
                    "role": "system",
                    "tags": [],
                    "permanent": False,
                    "similarity": 0.05,
                },
            ]

    from alfred.context import ContextBuilder

    context_builder = ContextBuilder(
        store=MockStore(),
        memory_budget=32000,
        min_similarity=0.6,
    )

    memories, similarities, scores = await context_builder.search_memories(
        [0.1] * 768,
        top_k=10,
    )

    assert [memory.entry_id for memory in memories] == ["mem-close"]
    assert similarities["mem-close"] == 0.95
    assert "mem-far" not in similarities
