# PRD: M4 - Vector Search & Context Injection

## Overview

**Issue**: #14  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #13 (M3: Memory Foundation)  
**Status**: Planning  
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

- [ ] `src/search.py` - Vector similarity search
- [ ] Cosine similarity implementation
- [ ] Hybrid scoring algorithm
- [ ] Token budget tracking
- [ ] Context injection into prompts
- [ ] Deduplication of similar memories
- [ ] >80% relevance accuracy in tests

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
import numpy as np
from datetime import datetime, timedelta
from src.types import MemoryEntry
from src.embeddings import EmbeddingClient


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    vec_a = np.array(a)
    vec_b = np.array(b)
    return float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)))


class MemorySearcher:
    def __init__(
        self,
        embedder: EmbeddingClient,
        context_limit: int = 20,
        min_similarity: float = 0.7,
    ) -> None:
        self.embedder = embedder
        self.context_limit = context_limit
        self.min_similarity = min_similarity
    
    async def search(
        self,
        query: str,
        memories: list[MemoryEntry],
    ) -> list[MemoryEntry]:
        """Search memories by semantic similarity."""
        if not memories:
            return []
        
        # Embed query
        query_embedding = await self.embedder.embed(query)
        
        # Score all memories
        scored = []
        for memory in memories:
            if memory.embedding is None:
                continue
            
            similarity = cosine_similarity(query_embedding, memory.embedding)
            if similarity < self.min_similarity:
                continue
            
            score = self._hybrid_score(memory, similarity)
            scored.append((score, memory))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Return top results
        return [m for _, m in scored[:self.context_limit]]
    
    def _hybrid_score(
        self,
        memory: MemoryEntry,
        similarity: float,
    ) -> float:
        """Combine similarity, recency, and importance."""
        # Recency decay (older = lower score)
        age_days = (datetime.now() - memory.timestamp).days
        recency = np.exp(-age_days / 30)  # 30-day half-life
        
        # Weighted combination
        score = (
            similarity * 0.5 +      # Semantic relevance
            recency * 0.3 +         # Time decay
            memory.importance * 0.2  # User-marked importance
        )
        
        return score
    
    def deduplicate(
        self,
        memories: list[MemoryEntry],
        threshold: float = 0.95,
    ) -> list[MemoryEntry]:
        """Remove near-duplicate memories."""
        if not memories:
            return []
        
        unique = [memories[0]]
        
        for memory in memories[1:]:
            if memory.embedding is None:
                continue
            
            # Check similarity to all kept memories
            is_duplicate = False
            for kept in unique:
                if kept.embedding is None:
                    continue
                sim = cosine_similarity(memory.embedding, kept.embedding)
                if sim > threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(memory)
        
        return unique


class ContextBuilder:
    """Build prompt context with memory injection."""
    
    def __init__(self, searcher: MemorySearcher) -> None:
        self.searcher = searcher
    
    async def build_context(
        self,
        query: str,
        memories: list[MemoryEntry],
        system_prompt: str,
        token_budget: int = 8000,
    ) -> str:
        """Build full context with relevant memories."""
        # Search for relevant memories
        relevant = await self.searcher.search(query, memories)
        relevant = self.searcher.deduplicate(relevant)
        
        # Build memory section
        memory_lines = ["# RELEVANT MEMORIES\n"]
        for mem in relevant:
            prefix = "User" if mem.role == "user" else "Assistant"
            date = mem.timestamp.strftime("%Y-%m-%d")
            memory_lines.append(f"[{date}] {prefix}: {mem.content}")
        
        memory_section = "\n".join(memory_lines)
        
        # Combine
        parts = [
            system_prompt,
            memory_section,
            "\n# CURRENT CONVERSATION\n",
        ]
        
        return "\n\n".join(parts)
```

---

## Updated Context (src/context.py additions)

```python
# Add to ContextLoader class

from src.search import MemorySearcher, ContextBuilder


class ContextLoader:
    def __init__(self, config: Config, searcher: MemorySearcher) -> None:
        self.config = config
        self.searcher = searcher
        self.builder = ContextBuilder(searcher)
    
    async def assemble_with_memories(
        self,
        query: str,
        all_memories: list[MemoryEntry],
    ) -> str:
        """Assemble context with memory search."""
        files = self.load_all()
        system_prompt = self._build_system_prompt(files)
        
        return await self.builder.build_context(
            query=query,
            memories=all_memories,
            system_prompt=system_prompt,
        )
```

---

## Tests

```python
# tests/test_search.py
import pytest
import numpy as np
from datetime import datetime, timedelta
from src.search import cosine_similarity, MemorySearcher
from src.types import MemoryEntry


def test_cosine_similarity_identical():
    vec = [1.0, 0.0, 0.0]
    assert cosine_similarity(vec, vec) == 1.0


def test_cosine_similarity_orthogonal():
    vec_a = [1.0, 0.0]
    vec_b = [0.0, 1.0]
    assert cosine_similarity(vec_a, vec_b) == 0.0


@pytest.fixture
def mock_embedder():
    class MockEmbedder:
        async def embed(self, text: str) -> list[float]:
            # Deterministic embedding based on text hash
            np.random.seed(hash(text) % 2**32)
            vec = np.random.randn(1536)
            return (vec / np.linalg.norm(vec)).tolist()
    
    return MockEmbedder()


@pytest.mark.asyncio
async def test_search_returns_relevant_memories(mock_embedder):
    searcher = MemorySearcher(mock_embedder, context_limit=5)
    
    # Create memories with different embeddings
    memories = [
        MemoryEntry(
            timestamp=datetime.now(),
            role="user",
            content="I love Python programming",
            embedding=[0.9] * 1536,
        ),
        MemoryEntry(
            timestamp=datetime.now(),
            role="user",
            content="My favorite color is blue",
            embedding=[0.1] * 1536,
        ),
    ]
    
    results = await searcher.search("Tell me about my coding projects", memories)
    
    # Should prefer Python memory
    assert len(results) > 0
    assert "Python" in results[0].content


@pytest.mark.asyncio
async def test_deduplication_removes_similar(mock_embedder):
    searcher = MemorySearcher(mock_embedder)
    
    memories = [
        MemoryEntry(
            timestamp=datetime.now(),
            role="user",
            content="I like Python",
            embedding=[0.9] * 1536,
        ),
        MemoryEntry(
            timestamp=datetime.now(),
            role="user",
            content="I like Python coding",
            embedding=[0.91] * 1536,
        ),
    ]
    
    unique = searcher.deduplicate(memories, threshold=0.95)
    assert len(unique) == 1
```

---

## Success Criteria

- [ ] Cosine similarity calculates correctly
- [ ] Hybrid scoring balances relevance, recency, importance
- [ ] Deduplication removes near-duplicates
- [ ] Context builds within token budget
- [ ] Search accuracy exceeds 80% in tests
- [ ] All type-safe
