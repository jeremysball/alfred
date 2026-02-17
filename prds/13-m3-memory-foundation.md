# PRD: M3 - Memory System Foundation

## Overview

**Issue**: #13  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #12 (M2: Core Infrastructure)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Implement JSON-based daily memory storage with OpenAI embeddings.

---

## Problem Statement

Alfred needs to persist every interaction with semantic embeddings for later retrieval. Store conversations in dated JSON files with OpenAI embeddings.

---

## Solution

Create memory system with:
1. Daily JSON file storage
2. OpenAI embedding generation
3. IMPORTANT.md support
4. Async I/O for performance

---

## Acceptance Criteria

- [ ] `src/embeddings.py` - OpenAI embedding client
- [ ] `src/memory.py` - Memory CRUD operations
- [ ] Generate embeddings on every interaction
- [ ] Store to `memory/YYYY-MM-DD.json`
- [ ] IMPORTANT.md read/write
- [ ] Async file operations
- [ ] Handle embedding API failures (fail fast)

---

## File Structure

```
src/
├── embeddings.py    # OpenAI embedding client
└── memory.py        # Memory operations

memory/
├── 2026-02-16.json  # Daily memory files
└── 2026-02-17.json
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
import aiofiles
from datetime import datetime
from pathlib import Path
from src.types import MemoryEntry, DailyMemory
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
        return self.memory_dir / f"{date}.json"
    
    async def load_daily(self, date: str | None = None) -> DailyMemory:
        """Load daily memory file."""
        path = self._daily_path(date)
        if not path.exists():
            return DailyMemory(date=date or datetime.now().strftime("%Y-%m-%d"))
        
        async with aiofiles.open(path, "r") as f:
            content = await f.read()
            data = json.loads(content)
            return DailyMemory.model_validate(data)
    
    async def save_daily(self, memory: DailyMemory) -> None:
        """Save daily memory file."""
        path = self._daily_path(memory.date)
        async with aiofiles.open(path, "w") as f:
            await f.write(memory.model_dump_json(indent=2))
    
    async def add_entry(
        self,
        role: str,
        content: str,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """Add entry with auto-generated embedding."""
        embedding = await self.embedder.embed(content)
        
        entry = MemoryEntry(
            timestamp=datetime.now(),
            role=role,  # type: ignore
            content=content,
            embedding=embedding,
            importance=importance,
            tags=tags or [],
        )
        
        daily = await self.load_daily()
        daily.entries.append(entry)
        await self.save_daily(daily)
        
        return entry
    
    async def load_all_memories(self) -> list[MemoryEntry]:
        """Load all memories across all days."""
        entries = []
        for path in self.memory_dir.glob("*.json"):
            daily = await self.load_daily(path.stem)
            entries.extend(daily.entries)
        return entries
```

---

## IMPORTANT.md Support

```python
# Add to src/memory.py

class ImportantMemory:
    """Curated long-term memory."""
    
    def __init__(self, config: Config, embedder: EmbeddingClient) -> None:
        self.path = Path("IMPORTANT.md")
        self.config = config
        self.embedder = embedder
    
    async def load(self) -> str:
        """Load IMPORTANT.md content."""
        if not self.path.exists():
            return ""
        async with aiofiles.open(self.path, "r") as f:
            return await f.read()
    
    async def append(self, content: str) -> None:
        """Append to IMPORTANT.md."""
        async with aiofiles.open(self.path, "a") as f:
            await f.write(f"\n\n{content}\n")
    
    async def get_entries(self) -> list[MemoryEntry]:
        """Parse IMPORTANT.md into memory entries with embeddings."""
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
                tags=["important"],
            ))
        
        return entries
```

---

## Tests

```python
# tests/test_memory.py
import pytest
from datetime import datetime
from src.memory import MemoryStore
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
async def test_add_entry_creates_daily_file(mock_config, mock_embedder, tmp_path):
    mock_config.memory_dir = tmp_path / "memory"
    store = MemoryStore(mock_config, mock_embedder)
    
    entry = await store.add_entry("user", "Hello Alfred")
    
    assert entry.content == "Hello Alfred"
    assert entry.embedding is not None
    assert len(entry.embedding) == 1536
    
    today = datetime.now().strftime("%Y-%m-%d")
    daily_path = tmp_path / "memory" / f"{today}.json"
    assert daily_path.exists()
```

---

## Success Criteria

- [ ] Embeddings generate for all entries
- [ ] Daily files create automatically
- [ ] IMPORTANT.md loads and parses
- [ ] Async operations work correctly
- [ ] All tests pass with golden vectors
- [ ] Type-safe throughout
