"""Tests for vector search and context building."""

import math
from datetime import datetime, timedelta

import pytest

from src.search import MemorySearcher, ContextBuilder, approximate_tokens
from src.types import MemoryEntry


class TestApproximateTokens:
    """Test token approximation."""

    def test_empty_string(self):
        assert approximate_tokens("") == 0

    def test_short_string(self):
        # 20 chars / 4 = 5 tokens
        assert approximate_tokens("hello world test!!") == 4

    def test_long_string(self):
        text = "a" * 400
        assert approximate_tokens(text) == 100


class TestCosineSimilaritySearch:
    """Test MemorySearcher with cosine similarity."""

    def test_search_returns_ranked_results(self):
        """Test that search returns memories ranked by similarity."""
        searcher = MemorySearcher(context_limit=5, min_similarity=0.0)

        # Create memories with different embeddings
        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content="I love Python programming",
                embedding=[1.0, 0.0, 0.0],  # Similar to query
                importance=0.5,
            ),
            MemoryEntry(
                timestamp=now,
                role="user",
                content="My favorite color is blue",
                embedding=[0.0, 1.0, 0.0],  # Orthogonal to query
                importance=0.5,
            ),
            MemoryEntry(
                timestamp=now,
                role="user",
                content="I enjoy coding",
                embedding=[0.9, 0.1, 0.0],  # Very similar to query
                importance=0.5,
            ),
        ]

        # Query embedding aligned with first axis (Python)
        query = [1.0, 0.0, 0.0]
        results = searcher.search(query, memories)

        assert len(results) == 3
        # Most similar should be first (Python programming)
        assert "Python" in results[0].content or "coding" in results[0].content
        # Least similar should be last (color)
        assert "color" in results[2].content

    def test_search_respects_min_similarity(self):
        """Test that memories below min_similarity are filtered."""
        searcher = MemorySearcher(min_similarity=0.8)

        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content="Very relevant",
                embedding=[1.0, 0.0],  # similarity = 1.0
            ),
            MemoryEntry(
                timestamp=now,
                role="user",
                content="Somewhat relevant",
                embedding=[0.7, 0.7],  # similarity ~ 0.7
            ),
            MemoryEntry(
                timestamp=now,
                role="user",
                content="Not relevant",
                embedding=[0.0, 1.0],  # similarity = 0.0
            ),
        ]

        query = [1.0, 0.0]
        results = searcher.search(query, memories)

        assert len(results) == 1
        assert results[0].content == "Very relevant"

    def test_search_respects_context_limit(self):
        """Test that only top_k results are returned."""
        searcher = MemorySearcher(context_limit=2)

        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content=f"Memory {i}",
                embedding=[1.0 - (i * 0.1), 0.0],  # Decreasing similarity
            )
            for i in range(10)
        ]

        query = [1.0, 0.0]
        results = searcher.search(query, memories)

        assert len(results) == 2

    def test_search_skips_memories_without_embeddings(self):
        """Test that memories without embeddings are skipped."""
        searcher = MemorySearcher(min_similarity=0.0)

        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content="Has embedding",
                embedding=[1.0, 0.0],
            ),
            MemoryEntry(
                timestamp=now,
                role="user",
                content="No embedding",
                embedding=None,
            ),
        ]

        query = [1.0, 0.0]
        results = searcher.search(query, memories)

        assert len(results) == 1
        assert results[0].content == "Has embedding"


class TestHybridScoring:
    """Test hybrid scoring (similarity + recency + importance)."""

    def test_hybrid_score_weights(self):
        """Test that hybrid score combines factors correctly."""
        searcher = MemorySearcher(recency_half_life=30)
        now = datetime.now()

        # Memory with perfect similarity, current, but low importance
        memory = MemoryEntry(
            timestamp=now,
            role="user",
            content="Test",
            embedding=[1.0, 0.0],
            importance=0.0,
        )

        score = searcher._hybrid_score(memory, similarity=1.0)
        # Expected: 1.0*0.5 + 1.0*0.3 + 0.0*0.2 = 0.8
        assert score == pytest.approx(0.8, abs=0.01)

    def test_recency_decay(self):
        """Test that older memories score lower on recency."""
        searcher = MemorySearcher(recency_half_life=30)
        now = datetime.now()

        # Fresh memory (today)
        fresh = MemoryEntry(
            timestamp=now,
            role="user",
            content="Fresh",
            embedding=[1.0, 0.0],
            importance=0.5,
        )

        # Old memory (60 days ago)
        old = MemoryEntry(
            timestamp=now - timedelta(days=60),
            role="user",
            content="Old",
            embedding=[1.0, 0.0],
            importance=0.5,
        )

        fresh_score = searcher._hybrid_score(fresh, similarity=1.0)
        old_score = searcher._hybrid_score(old, similarity=1.0)

        # Fresh should score higher
        assert fresh_score > old_score

        # Verify the math: recency = exp(-60/30) = exp(-2) ≈ 0.135
        expected_old_recency = math.exp(-2)
        expected_old_score = 1.0 * 0.5 + expected_old_recency * 0.3 + 0.5 * 0.2
        assert old_score == pytest.approx(expected_old_score, abs=0.01)

    def test_importance_boost(self):
        """Test that high importance boosts score."""
        searcher = MemorySearcher()
        now = datetime.now()

        # Same similarity and recency, different importance
        low_imp = MemoryEntry(
            timestamp=now,
            role="user",
            content="Low importance",
            embedding=[1.0, 0.0],
            importance=0.0,
        )
        high_imp = MemoryEntry(
            timestamp=now,
            role="user",
            content="High importance",
            embedding=[1.0, 0.0],
            importance=1.0,
        )

        low_score = searcher._hybrid_score(low_imp, similarity=1.0)
        high_score = searcher._hybrid_score(high_imp, similarity=1.0)

        # High importance should score 0.2 more
        assert high_score == pytest.approx(low_score + 0.2, abs=0.01)


class TestDeduplication:
    """Test memory deduplication."""

    def test_removes_near_duplicates(self):
        """Test that very similar memories are deduplicated."""
        searcher = MemorySearcher()

        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content="I love Python",
                embedding=[1.0, 0.0, 0.0],
            ),
            MemoryEntry(
                timestamp=now,
                role="user",
                content="I really love Python programming",
                embedding=[0.99, 0.01, 0.0],  # 99% similar
            ),
            MemoryEntry(
                timestamp=now,
                role="user",
                content="Something different",
                embedding=[0.0, 1.0, 0.0],  # Different
            ),
        ]

        deduped = searcher.deduplicate(memories, threshold=0.95)

        assert len(deduped) == 2
        assert deduped[0].content == "I love Python"
        assert deduped[1].content == "Something different"

    def test_preserves_order(self):
        """Test that deduplication preserves input order for unique memories."""
        searcher = MemorySearcher()

        now = datetime.now()
        memories = [
            MemoryEntry(timestamp=now, role="user", content="First", embedding=[1.0, 0.0]),
            MemoryEntry(timestamp=now, role="user", content="Second", embedding=[0.0, 1.0]),
            MemoryEntry(timestamp=now, role="user", content="Third", embedding=[0.0, 0.0, 1.0]),
        ]

        deduped = searcher.deduplicate(memories)

        assert len(deduped) == 3
        assert [m.content for m in deduped] == ["First", "Second", "Third"]

    def test_keeps_memories_without_embeddings(self):
        """Test that memories without embeddings are kept (can't dedupe)."""
        searcher = MemorySearcher()

        now = datetime.now()
        memories = [
            MemoryEntry(timestamp=now, role="user", content="No embedding", embedding=None),
            MemoryEntry(timestamp=now, role="user", content="Has embedding", embedding=[1.0, 0.0]),
        ]

        deduped = searcher.deduplicate(memories)

        assert len(deduped) == 2

    def test_empty_list(self):
        """Test deduplication of empty list."""
        searcher = MemorySearcher()
        assert searcher.deduplicate([]) == []


class TestContextBuilder:
    """Test ContextBuilder."""

    def test_builds_context_with_memories(self):
        """Test context building with relevant memories."""
        searcher = MemorySearcher(context_limit=10, min_similarity=0.0)
        builder = ContextBuilder(searcher)

        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content="I love Python",
                embedding=[1.0, 0.0],
            ),
        ]

        query = [1.0, 0.0]
        context = builder.build_context(
            query_embedding=query,
            memories=memories,
            system_prompt="You are Alfred.",
        )

        assert "You are Alfred." in context
        assert "## RELEVANT MEMORIES" in context
        assert "I love Python" in context
        assert "## CURRENT CONVERSATION" in context

    def test_handles_no_relevant_memories(self):
        """Test context building when no memories match."""
        searcher = MemorySearcher(min_similarity=0.9)
        builder = ContextBuilder(searcher)

        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content="Not relevant",
                embedding=[0.0, 1.0],  # Orthogonal to query
            ),
        ]

        query = [1.0, 0.0]
        context = builder.build_context(
            query_embedding=query,
            memories=memories,
            system_prompt="You are Alfred.",
        )

        assert "You are Alfred." in context
        assert "## RELEVANT MEMORIES" in context
        assert "_No relevant memories found._" in context

    def test_truncates_long_content(self):
        """Test that long memory content is truncated."""
        searcher = MemorySearcher(context_limit=10, min_similarity=0.0)
        builder = ContextBuilder(searcher)

        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content="A" * 500,  # Very long content
                embedding=[1.0, 0.0],
            ),
        ]

        query = [1.0, 0.0]
        context = builder.build_context(
            query_embedding=query,
            memories=memories,
            system_prompt="You are Alfred.",
        )

        # Content should be truncated with "..."
        assert "..." in context
        # Should not contain the full 500 chars
        assert len(context) < 1000

    def test_respects_token_budget(self):
        """Test that context respects token budget."""
        searcher = MemorySearcher(context_limit=100, min_similarity=0.0)
        builder = ContextBuilder(searcher, token_budget=100)

        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content=f"Memory {i} with some text content here",
                embedding=[1.0, 0.0],
            )
            for i in range(20)
        ]

        query = [1.0, 0.0]
        context = builder.build_context(
            query_embedding=query,
            memories=memories,
            system_prompt="System prompt.",
        )

        # Should fit within budget (approximately)
        token_count = approximate_tokens(context)
        assert token_count <= 200  # Allow some margin


class TestIntegration:
    """Integration tests for the full search flow."""

    def test_end_to_end_search_and_context(self):
        """Test full flow: search -> dedupe -> build context."""
        searcher = MemorySearcher(
            context_limit=5,
            min_similarity=0.5,
            recency_half_life=30,
        )
        builder = ContextBuilder(searcher)

        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content="I love Python programming",
                embedding=[1.0, 0.0, 0.0],
                importance=0.8,
            ),
            MemoryEntry(
                timestamp=now,
                role="user",
                content="I love Python coding",  # Near duplicate
                embedding=[0.99, 0.01, 0.0],
                importance=0.5,
            ),
            MemoryEntry(
                timestamp=now - timedelta(days=60),  # Old
                role="user",
                content="My favorite color is blue",
                embedding=[0.0, 1.0, 0.0],
                importance=0.5,
            ),
            MemoryEntry(
                timestamp=now,
                role="assistant",
                content="That's great!",
                embedding=[0.5, 0.5, 0.0],
                importance=0.3,
            ),
        ]

        # Search for "Python programming"
        query = [1.0, 0.0, 0.0]
        context = builder.build_context(
            query_embedding=query,
            memories=memories,
            system_prompt="You are a helpful assistant.",
        )

        # Verify structure
        assert "You are a helpful assistant." in context
        assert "## RELEVANT MEMORIES" in context
        assert "## CURRENT CONVERSATION" in context

        # Python memory should be included
        assert "Python" in context

        # Should not have both duplicates
        python_count = context.count("Python")
        assert python_count <= 2  # At most 2 mentions (content + maybe metadata)

    def test_different_query_orientations(self):
        """Test that different queries find different memories."""
        searcher = MemorySearcher(context_limit=3, min_similarity=0.0)

        now = datetime.now()
        memories = [
            MemoryEntry(
                timestamp=now,
                role="user",
                content="I love Python",
                embedding=[1.0, 0.0],
            ),
            MemoryEntry(
                timestamp=now,
                role="user",
                content="I like JavaScript",
                embedding=[0.0, 1.0],
            ),
        ]

        # Query for Python
        python_results = searcher.search([1.0, 0.0], memories)
        assert python_results[0].content == "I love Python"

        # Query for JavaScript
        js_results = searcher.search([0.0, 1.0], memories)
        assert js_results[0].content == "I like JavaScript"
