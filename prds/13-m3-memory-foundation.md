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

Alfred needs to persist every interaction with semantic embeddings for later retrieval. Store conversations in dated Markdown files with OpenAI embeddings for semantic search.

---

## Solution

Create memory system with:
1. Daily Markdown file storage (human-readable)
2. OpenAI embedding generation
3. MEMORY.md support (curated long-term memory)
4. Async I/O for performance

---

## Acceptance Criteria

- [ ] `src/embeddings.py` - OpenAI embedding client
- [ ] `src/memory.py` - Memory CRUD operations
- [ ] Generate embeddings on every interaction
- [ ] Store to `memory/YYYY-MM-DD.md` (Markdown format)
- [ ] MEMORY.md read/write (curated long-term memory)
- [ ] Async file operations
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
import aiofiles
from datetime import datetime
from pathlib import Path
from src.types import MemoryEntry
from src.config import Config
from src.embeddings import EmbeddingClient


class MemoryStore:
    def __init__(self, config: Config, embedder: EmbeddingClient) -> None:
        self.config = config
        self.embedder = embedder
        self.memory_dir = config.memory_dir
        self.memory_dir.mkdir(exist_ok=True)
    
    def _daily_path(self, date: str | None = None) -> Path:
        """Get path for daily memory file."""
        date = date or datetime.now().strftime("%Y-%m-%d")
        return self.memory_dir / f"{date}.md"
    
    async def load_daily(self, date: str | None = None) -> str:
        """Load daily memory file as raw Markdown."""
        path = self._daily_path(date)
        if not path.exists():
            return ""
        async with aiofiles.open(path, "r") as f:
            return await f.read()
    
    async def append_to_daily(
        self,
        role: str,
        content: str,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> None:
        """Append entry to daily Markdown file."""
        path = self._daily_path()
        timestamp = datetime.now().strftime("%H:%M")
        
        # Format as Markdown
        entry_lines = [
            f"\n## {timestamp} - {role.title()}\n",
            content,
        ]
        
        # Add metadata as HTML comment
        if importance != 0.5 or tags:
            metadata = {"importance": importance}
            if tags:
                metadata["tags"] = tags
            entry_lines.append(f"\n<!-- metadata: {metadata} -->")
        
        async with aiofiles.open(path, "a") as f:
            await f.write("\n".join(entry_lines))
    
    async def add_entry(
        self,
        role: str,
        content: str,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """Add entry with auto-generated embedding."""
        embedding = await self.embedder.embed(content)
        
        await self.append_to_daily(role, content, importance, tags)
        
        return MemoryEntry(
            timestamp=datetime.now(),
            role=role,  # type: ignore
            content=content,
            embedding=embedding,
            importance=importance,
            tags=tags or [],
        )
    
    async def load_all_daily_content(self) -> str:
        """Load all daily Markdown files concatenated."""
        contents = []
        for path in sorted(self.memory_dir.glob("*.md")):
            async with aiofiles.open(path, "r") as f:
                content = await f.read()
                if content.strip():
                    contents.append(f"# {path.stem}\n\n{content}")
        return "\n\n---\n\n".join(contents)
```

---

## MEMORY.md Support

```python
# Add to src/memory.py

class CuratedMemory:
    """Curated long-term memory (MEMORY.md)."""
    
    def __init__(self, config: Config, embedder: EmbeddingClient) -> None:
        self.path = Path("MEMORY.md")
        self.config = config
        self.embedder = embedder
    
    async def load(self) -> str:
        """Load MEMORY.md content."""
        if not self.path.exists():
            return ""
        async with aiofiles.open(self.path, "r") as f:
            return await f.read()
    
    async def append(self, content: str) -> None:
        """Append to MEMORY.md."""
        async with aiofiles.open(self.path, "a") as f:
            await f.write(f"\n\n{content}\n")
    
    async def get_entries(self) -> list[MemoryEntry]:
        """Parse MEMORY.md into memory entries with embeddings."""
        content = await self.load()
        if not content:
            return []
        
        # Split by headers or entries
        sections = [s.strip() for s in content.split("\n\n") if s.strip()]
        
        entries = []
        for section in sections:
            embedding = await self.embedder.embed(section)
            entries.append(MemoryEntry(
                timestamp=datetime.now(),
                role="system",
                content=section,
                embedding=embedding,
                importance=1.0,  # High importance
                tags=["curated"],
            ))
        
        return entries
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
