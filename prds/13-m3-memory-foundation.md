# PRD: M3 - Memory System Foundation

## Overview

**Issue**: #13  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #12 (M2: Core Infrastructure)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Implement Markdown-based daily memory storage with OpenAI embeddings.

---

## Problem Statement

Alfred needs to persist distilled insights from conversations with semantic embeddings for later retrieval. Store distilled memories in dated Markdown files with OpenAI embeddings for semantic search.

---

## Solution

Create memory system with:
1. Daily Markdown file storage (human-readable, contains distilled insights)
2. Distillation process creates daily logs from conversation summaries
3. OpenAI embedding generation for semantic search
4. MEMORY.md support (curated long-term memory for durable facts)
5. Async I/O for performance

### Distillation Process

Daily logs are created by the **distillation process**, not raw conversation logging:
- Run before compacting long conversations
- Run at end of each day over all conversations
- Extracts key facts, decisions, and context into `MemoryEntry` objects
- Writes distilled insights to `memory/YYYY-MM-DD.md`

---

## Acceptance Criteria

- [ ] `src/embeddings.py` - OpenAI embedding client with cosine similarity
- [ ] `src/memory.py` - Memory CRUD operations for daily logs and MEMORY.md
- [ ] `write_daily_log()` - Write distilled entries to daily Markdown file
- [ ] `parse_daily_log()` - Parse Markdown back into `MemoryEntry` objects with embeddings
- [ ] `search_memories()` - Semantic search across daily logs and MEMORY.md
- [ ] MEMORY.md read/write for curated long-term memory
- [ ] Async file operations throughout
- [ ] Handle embedding API failures (fail fast)

---

## File Structure

```
src/
├── embeddings.py    # OpenAI embedding client
└── memory.py        # Memory operations

memory/
├── 2026-02-16.md    # Daily memory files (Markdown)
├── 2026-02-17.md
└── ...

MEMORY.md            # Curated long-term memory
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
import re
from datetime import datetime
from pathlib import Path

import aiofiles

from src.config import Config
from src.embeddings import EmbeddingClient
from src.types import MemoryEntry


class MemoryStore:
    """Store and retrieve memories from daily logs and MEMORY.md."""

    def __init__(self, config: Config, embedder: EmbeddingClient) -> None:
        self.config = config
        self.embedder = embedder
        self.memory_dir = config.memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.curated_path = Path("MEMORY.md")

    def _daily_path(self, date: str | None = None) -> Path:
        """Get path for daily memory file (YYYY-MM-DD.md)."""
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        return self.memory_dir / f"{date_str}.md"

    async def write_daily_log(
        self,
        date: str,
        entries: list[MemoryEntry],
    ) -> Path:
        """Write distilled entries to a daily log file.

        Called by the distillation process after summarizing conversations.
        Overwrites existing file for that date.
        """
        path = self._daily_path(date)
        lines = [f"# {date}\n"]

        for entry in entries:
            timestamp = entry.timestamp.strftime("%H:%M")
            lines.append(f"\n## {timestamp} - {entry.role.title()}\n")
            lines.append(entry.content)
            if entry.importance != 0.5 or entry.tags:
                metadata = {"importance": entry.importance}
                if entry.tags:
                    metadata["tags"] = entry.tags
                lines.append(f"\n<!-- metadata: {metadata} -->")

        async with aiofiles.open(path, "w") as f:
            await f.write("\n".join(lines))

        return path

    async def read_daily_log(self, date: str | None = None) -> str:
        """Read a daily log file as raw Markdown."""
        path = self._daily_path(date)
        if not path.exists():
            return ""
        async with aiofiles.open(path, "r") as f:
            return await f.read()

    async def parse_daily_log(self, date: str | None = None) -> list[MemoryEntry]:
        """Parse a daily log into MemoryEntry objects with embeddings."""
        content = await self.read_daily_log(date)
        if not content:
            return []

        entries = []
        # Split on ## headers (each entry)
        sections = re.split(r"\n## ", content)[1:]  # Skip title

        for section in sections:
            lines = section.strip().split("\n")
            header = lines[0]  # "HH:MM - Role"
            body = "\n".join(lines[1:]).strip()

            # Parse header and extract timestamp, role
            # Parse metadata from HTML comment <!-- metadata: {...} -->
            # Generate embedding for content
            # Return list of MemoryEntry objects

        return entries

    async def search_memories(
        self,
        query: str,
        top_k: int = 10,
        include_curated: bool = True,
    ) -> list[MemoryEntry]:
        """Search all memories by semantic similarity to query."""
        # 1. Embed query
        # 2. Load all daily logs and MEMORY.md
        # 3. Score by cosine similarity (boosted by importance)
        # 4. Return top-k entries
        pass
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

- [ ] Embeddings generate for all entries
- [ ] Daily Markdown files create automatically
- [ ] MEMORY.md loads and parses
- [ ] Async operations work correctly
- [ ] All tests pass with golden vectors
- [ ] Type-safe throughout

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Memory files are Markdown, not JSON | Human-readable, matches OpenClaw pattern | File format, parsing logic |
| 2026-02-17 | Long-term memory is MEMORY.md | Matches OpenClaw pattern | Renamed from IMPORTANT.md |
| 2026-02-17 | Daily logs contain distilled insights, not raw chat | Raw conversations too noisy; distilled facts are searchable and useful | Memory format, distillation process |
| 2026-02-17 | Distillation process creates daily logs | Run before compact or end-of-day; extracts key facts, decisions, context | Workflow, when to write memories |
| 2026-02-17 | HTML comments for metadata in Markdown | Human-readable with parseable structured data | File format, metadata storage |
| 2026-02-17 | MemoryEntry as the retrieval unit | Self-contained insight with embedding, importance, tags | Search granularity, API design |
