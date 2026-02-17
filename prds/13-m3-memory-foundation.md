# PRD: M3 - Memory System Foundation

## Overview

**Issue**: #13  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #12 (M2: Core Infrastructure)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Implement unified memory storage with OpenAI embeddings for semantic retrieval.

---

## Problem Statement

Alfred needs to persist distilled insights from conversations with semantic embeddings for later retrieval. Store all memories in a unified, searchable store with date as metadata (not structure).

---

## Solution

Create unified memory system with:
1. **Unified storage** (`memories.jsonl`) - All memories in one searchable file
2. **Date as metadata** - Timestamp field, not file structure
3. **Distillation process** - Creates `MemoryEntry` objects from conversations
4. **OpenAI embeddings** - For semantic search
5. **MEMORY.md** - Curated long-term memory (separate, for durable facts)
6. **Async I/O** - For performance

### Distillation Process

Memories are created by the **distillation process**, not raw conversation logging:
- Run before compacting long conversations
- Run at end of each day over all conversations  
- Extracts key facts, decisions, and context into `MemoryEntry` objects
- Writes to unified store via `add_entries()`

### Why Unified Storage?

- Single searchable space (no need to open N files)
- Date is just another filter (query by date range)
- Simpler code path (one read/write pattern)
- Foundation for future indexing (FAISS, Annoy, etc.)
- Can always generate daily views from unified store

---

## Acceptance Criteria

- [ ] `src/embeddings.py` - OpenAI embedding client with cosine similarity
- [ ] `src/memory.py` - Unified memory store
- [ ] `add_entries()` - Write distilled entries to unified store with auto-embedding
- [ ] `search()` - Semantic search with optional date filtering
- [ ] `filter_by_date()` - Query memories by date range
- [ ] `iter_entries()` - Memory-efficient iteration over all memories
- [ ] MEMORY.md read/write/search for curated long-term memory
- [ ] Async file operations throughout
- [ ] Handle embedding API failures (fail fast)

---

## File Structure

```
src/
├── embeddings.py    # OpenAI embedding client with cosine similarity
└── memory.py        # Unified memory store

memory/
└── memories.jsonl   # All memories (one per line, JSON format)

MEMORY.md            # Curated long-term memory (Markdown)
```

### memories.jsonl Format

Each line is a JSON-serialized `MemoryEntry`:

```json
{"timestamp": "2026-02-17T14:30:00", "role": "user", "content": "I prefer Python", "embedding": [0.1, ...], "importance": 0.8, "tags": ["preferences"]}
```

---

## Embeddings (src/embeddings.py)

```python
import openai
from src.config import Config


class EmbeddingClient:
    def __init__(self, config: Config) -> None:
        self.client = openai.AsyncOpenAI(api_key=config.openai_api_key)
        self.model = config.embedding_model
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
            encoding_format="float",
        )
        return response.data[0].embedding
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            encoding_format="float",
        )
        return [item.embedding for item in response.data]
```

---

## Memory (src/memory.py)

```python
import json
from datetime import datetime, date
from pathlib import Path
from typing import AsyncIterator

import aiofiles

from src.config import Config
from src.embeddings import EmbeddingClient, cosine_similarity
from src.types import MemoryEntry


class MemoryStore:
    """Unified memory store with semantic search."""

    def __init__(self, config: Config, embedder: EmbeddingClient) -> None:
        self.config = config
        self.embedder = embedder
        self.memory_dir = config.memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memories_path = self.memory_dir / "memories.jsonl"
        self.curated_path = Path("MEMORY.md")

    async def add_entries(self, entries: list[MemoryEntry]) -> None:
        """Add entries to unified store. Auto-generates embeddings if needed."""
        # Batch embed entries without embeddings
        entries_to_embed = [e for e in entries if e.embedding is None]
        if entries_to_embed:
            embeddings = await self.embedder.embed_batch(
                [e.content for e in entries_to_embed]
            )
            for entry, embedding in zip(entries_to_embed, embeddings):
                entry.embedding = embedding

        # Append to JSONL
        async with aiofiles.open(self.memories_path, "a") as f:
            for entry in entries:
                line = json.dumps({
                    "timestamp": entry.timestamp.isoformat(),
                    "role": entry.role,
                    "content": entry.content,
                    "embedding": entry.embedding,
                    "importance": entry.importance,
                    "tags": entry.tags,
                })
                await f.write(line + "\n")

    async def get_all_entries(self) -> list[MemoryEntry]:
        """Load all entries."""
        entries = []
        async for entry in self.iter_entries():
            entries.append(entry)
        return entries

    async def iter_entries(self) -> AsyncIterator[MemoryEntry]:
        """Memory-efficient iteration."""
        if not self.memories_path.exists():
            return
        async with aiofiles.open(self.memories_path, "r") as f:
            async for line in f:
                line = line.strip()
                if line:
                    yield self._parse_entry(line)

    async def filter_by_date(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MemoryEntry]:
        """Filter entries by date range."""
        results = []
        async for entry in self.iter_entries():
            entry_date = entry.timestamp.date()
            if start_date and entry_date < start_date:
                continue
            if end_date and entry_date > end_date:
                continue
            results.append(entry)
        return results

    async def search(
        self,
        query: str,
        top_k: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MemoryEntry]:
        """Semantic search with optional date filtering."""
        query_embedding = await self.embedder.embed(query)

        scored = []
        async for entry in self.iter_entries():
            # Date filtering
            if start_date or end_date:
                entry_date = entry.timestamp.date()
                if start_date and entry_date < start_date:
                    continue
                if end_date and entry_date > end_date:
                    continue

            if entry.embedding:
                score = cosine_similarity(query_embedding, entry.embedding)
                score *= 0.7 + (entry.importance * 0.3)  # Boost by importance
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]
```

---

## MEMORY.md Support

```python
# Methods on MemoryStore class

async def read_curated_memory(self) -> str:
    """Load MEMORY.md content."""
    if not self.curated_path.exists():
        return ""
    async with aiofiles.open(self.curated_path, "r") as f:
        return await f.read()

async def write_curated_memory(self, content: str) -> None:
    """Write to MEMORY.md (overwrites existing content).

    Use this for durable, important memories that should persist
    across sessions and be loaded into every context.
    """
    async with aiofiles.open(self.curated_path, "w") as f:
        await f.write(content)

async def append_curated_memory(self, content: str) -> None:
    """Append to MEMORY.md."""
    async with aiofiles.open(self.curated_path, "a") as f:
        await f.write(f"\n\n{content}\n")

async def parse_curated_memory(self) -> list[MemoryEntry]:
    """Parse MEMORY.md into MemoryEntry objects with embeddings."""
    content = await self.read_curated_memory()
    if not content:
        return []

    # Each section becomes a MemoryEntry with:
    # - importance=1.0 (curated memories are high importance)
    # - tags=["curated"]
    # - Fresh embedding for semantic search
```

---

## Tests

```python
# tests/test_memory.py
import pytest
from datetime import datetime
from src.memory import MemoryStore, CuratedMemory
from src.embeddings import EmbeddingClient
from src.config import Config


@pytest.fixture
def mock_config(tmp_path):
    return Config(
        telegram_bot_token="test",
        openai_api_key="test",
        kimi_api_key="test",
        memory_dir=tmp_path / "memory",
    )


@pytest.fixture
def mock_embedder():
    class MockEmbedder:
        async def embed(self, text: str) -> list[float]:
            # Golden vector for testing
            return [0.1] * 1536
        
        async def embed_batch(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * 1536 for _ in texts]
    
    return MockEmbedder()  # type: ignore


@pytest.mark.asyncio
async def test_add_entry_creates_daily_markdown_file(mock_config, mock_embedder, tmp_path):
    mock_config.memory_dir = tmp_path / "memory"
    store = MemoryStore(mock_config, mock_embedder)
    
    entry = await store.add_entry("user", "Hello Alfred")
    
    assert entry.content == "Hello Alfred"
    assert entry.embedding is not None
    assert len(entry.embedding) == 1536
    
    today = datetime.now().strftime("%Y-%m-%d")
    daily_path = tmp_path / "memory" / f"{today}.md"
    assert daily_path.exists()
    
    content = await store.load_daily()
    assert "Hello Alfred" in content
    assert "User" in content


@pytest.mark.asyncio
async def test_curated_memory_loads_and_parses(mock_config, mock_embedder, tmp_path):
    # Create a test MEMORY.md
    memory_path = tmp_path / "MEMORY.md"
    memory_path.write_text("# Important\n\nUser prefers Python over JavaScript.\n")
    
    curated = CuratedMemory(mock_config, mock_embedder)
    curated.path = memory_path
    
    entries = await curated.get_entries()
    assert len(entries) == 1
    assert "Python" in entries[0].content
```

---

## Success Criteria

- [ ] Embeddings generate for all entries (batch or single)
- [ ] Unified JSONL store persists memories
- [ ] Date filtering works via metadata
- [ ] Semantic search returns relevant results
- [ ] MEMORY.md loads and parses
- [ ] Async operations work correctly
- [ ] All tests pass with golden vectors
- [ ] Type-safe throughout

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | **Unified storage** (`memories.jsonl`) instead of daily files | Single searchable space; date is metadata; simpler code; foundation for indexing | File structure, API design, search implementation |
| 2026-02-17 | JSONL format for unified store | Append-only, line-oriented, human-readable, easy to iterate without loading all | Storage format, memory efficiency |
| 2026-02-17 | Long-term memory is MEMORY.md | Matches OpenClaw pattern | Renamed from IMPORTANT.md |
| 2026-02-17 | Distilled insights, not raw chat | Raw conversations too noisy; distilled facts are searchable and useful | Memory format, distillation process |
| 2026-02-17 | Distillation process creates entries | Run before compact or end-of-day; extracts key facts, decisions, context | Workflow, when to write memories |
| 2026-02-17 | Date filtering via `start_date`/`end_date` params | Date is queryable metadata, not structural | API design, search implementation |
| 2026-02-17 | MemoryEntry as the retrieval unit | Self-contained insight with embedding, importance, tags | Search granularity, API design |
