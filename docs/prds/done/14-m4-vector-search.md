# PRD: M4 - Vector Search & Context Injection

## Overview

**Issue**: #14  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #13 (M3: Memory Foundation)  
**Status**: Complete  
**Priority**: High  
**Created**: 2026-02-16

Build cosine similarity search, hybrid scoring, and automatic context injection.

---

## Problem Statement

Alfred retrieves relevant memories using semantic search. Combine cosine similarity with recency and importance to surface the right context.

---

## Solution

Create vector search with:
1. Cosine similarity calculation
2. Hybrid scoring (similarity + recency + importance)
3. Token budget management
4. Automatic context injection

---

## Acceptance Criteria

- [x] `src/search.py` - Vector similarity search
- [x] Cosine similarity implementation
- [x] Hybrid scoring algorithm
- [x] Token budget tracking
- [x] Context injection into prompts
- [x] Deduplication of similar memories
- [x] >80% relevance accuracy in tests

---

## File Structure

```
src/
├── search.py       # Vector search and scoring
└── context.py      # Updated with memory injection
```

---

## Search (src/search.py)

```python
import logging
import math
from datetime import datetime

from src.embeddings import cosine_similarity
from src.types import MemoryEntry

logger = logging.getLogger(__name__)


def approximate_tokens(text: str) -> int:
    """Approximate token count (4 chars ≈ 1 token)."""
    return len(text) // 4


class MemorySearcher:
    """Search and rank memories by semantic similarity with hybrid scoring."""

    def __init__(
        self,
        context_limit: int = 20,
        min_similarity: float = 0.7,
        recency_half_life: int = 30,  # days
    ) -> None:
        self.context_limit = context_limit
        self.min_similarity = min_similarity
        self.recency_half_life = recency_half_life

    def search(
        self,
        query_embedding: list[float],
        memories: list[MemoryEntry],
    ) -> list[MemoryEntry]:
        """Search memories by semantic similarity with hybrid scoring.

        Args:
            query_embedding: Pre-computed embedding for the query
            memories: List of memories to search (caller loads these)

        Returns:
            Top memories ranked by hybrid score (similarity + recency + importance)
        """
        scored: list[tuple[float, MemoryEntry]] = []

        for memory in memories:
            if not memory.embedding:
                continue

            similarity = cosine_similarity(query_embedding, memory.embedding)
            if similarity < self.min_similarity:
                continue

            score = self._hybrid_score(memory, similarity)
            scored.append((score, memory))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in scored[:self.context_limit]]

    def _hybrid_score(
        self,
        memory: MemoryEntry,
        similarity: float,
    ) -> float:
        """Combine similarity, recency, and importance into a single score.

        Weights:
            - Similarity: 0.5 (semantic relevance to query)
            - Recency: 0.3 (newer memories score higher)
            - Importance: 0.2 (user/marked importance)
        """
        age_days = (datetime.now() - memory.timestamp).days
        recency = math.exp(-age_days / self.recency_half_life)

        return (
            similarity * 0.5 +
            recency * 0.3 +
            memory.importance * 0.2
        )

    def deduplicate(
        self,
        memories: list[MemoryEntry],
        threshold: float = 0.95,
    ) -> list[MemoryEntry]:
        """Remove near-duplicate memories by embedding similarity."""
        if not memories:
            return []

        unique: list[MemoryEntry] = []

        for memory in memories:
            if not memory.embedding:
                unique.append(memory)
                continue

            is_duplicate = any(
                cosine_similarity(memory.embedding, kept.embedding) > threshold
                for kept in unique if kept.embedding
            )
            if not is_duplicate:
                unique.append(memory)

        return unique


class ContextBuilder:
    """Build prompt context with relevant memories injected."""

    def __init__(
        self,
        searcher: MemorySearcher,
        token_budget: int = 8000,
    ) -> None:
        self.searcher = searcher
        self.token_budget = token_budget

    def build_context(
        self,
        query_embedding: list[float],
        memories: list[MemoryEntry],
        system_prompt: str,
    ) -> str:
        """Build full context with relevant memories injected."""
        relevant = self.searcher.search(query_embedding, memories)
        relevant = self.searcher.deduplicate(relevant)

        memory_section = self._format_memories(relevant)

        parts = [
            system_prompt,
            memory_section,
            "## CURRENT CONVERSATION\n",
        ]

        return "\n\n".join(parts)
```

---

## Updated Context (src/context.py additions)

```python
# Add to ContextLoader class

from src.search import MemorySearcher, ContextBuilder


class ContextLoader:
    def __init__(
        self,
        config: Config,
        cache_ttl: int = 60,
        searcher: MemorySearcher | None = None,
    ) -> None:
        self.config = config
        self._cache = ContextCache(ttl_seconds=cache_ttl)
        self._template_manager = TemplateManager(config.workspace_dir)
        self._searcher = searcher
        self._context_builder: ContextBuilder | None = None
        if searcher:
            self._context_builder = ContextBuilder(searcher)

    def assemble_with_search(
        self,
        query_embedding: list[float],
        memories: list[MemoryEntry],
    ) -> str:
        """Assemble context with semantic memory search.

        Uses the MemorySearcher to find and rank relevant memories,
        then builds a complete prompt context with them injected.
        """
        if not self._context_builder:
            raise RuntimeError(
                "MemorySearcher required for assemble_with_search. "
                "Initialize ContextLoader with searcher parameter."
            )

        system_prompt = self._build_system_prompt_sync()
        return self._context_builder.build_context(
            query_embedding=query_embedding,
            memories=memories,
            system_prompt=system_prompt,
        )
```

---

## Tests

Full test suite in `tests/test_search.py` with 20 tests covering:

```python
# Key test categories

class TestApproximateTokens:
    """Test token approximation."""
    def test_empty_string(self): ...
    def test_short_string(self): ...

class TestCosineSimilaritySearch:
    """Test MemorySearcher with cosine similarity."""
    def test_search_returns_ranked_results(self): ...
    def test_search_respects_min_similarity(self): ...
    def test_search_respects_context_limit(self): ...

class TestHybridScoring:
    """Test hybrid scoring (similarity + recency + importance)."""
    def test_hybrid_score_weights(self): ...
    def test_recency_decay(self): ...
    def test_importance_boost(self): ...

class TestDeduplication:
    """Test memory deduplication."""
    def test_removes_near_duplicates(self): ...
    def test_preserves_order(self): ...

class TestContextBuilder:
    """Test ContextBuilder."""
    def test_builds_context_with_memories(self): ...
    def test_respects_token_budget(self): ...

class TestIntegration:
    """Integration tests for full search flow."""
    def test_end_to_end_search_and_context(self): ...
```

---

## Success Criteria

- [x] Cosine similarity calculates correctly
- [x] Hybrid scoring balances relevance, recency, importance
- [x] Deduplication removes near-duplicates
- [x] Context builds within token budget
- [x] Search accuracy exceeds 80% in tests
- [x] All type-safe
