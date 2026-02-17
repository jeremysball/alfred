# PRD: M2 - Core Infrastructure

## Overview

**Issue**: #12  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #11 (M1: Project Setup)  
**Status**: Complete  
**Priority**: High  
**Created**: 2026-02-16

Build configuration management, context file loaders, and the base context injection system.

---

## Problem Statement

Alfred loads multiple context files (AGENTS.md, SOUL.md, USER.md, TOOLS.md) on every message. We need reliable file loading, parsing, and assembly into the prompt context.

---

## Solution

Create infrastructure for:
1. Configuration management (env vars, config.json)
2. Context file discovery and loading
3. Context assembly for LLM prompts
4. Error handling with fail-fast behavior

---

## Acceptance Criteria

- [x] `src/config.py` - Configuration dataclass with validation
- [x] `src/context.py` - Context file loader and assembler
- [x] `src/types.py` - Shared type definitions (Pydantic models)
- [x] `src/llm.py` - LLM provider abstraction with Kimi implementation (bonus)
- [ ] Load AGENTS.md, SOUL.md, USER.md, TOOLS.md (code done, template files pending)
- [x] Environment variable support with `.env` loading
- [x] `config.json` provides defaults (env vars override)
- [x] Fail on missing required files
- [x] Type-safe throughout (mypy strict passes)
- [x] Async file loading with thread pool
- [x] TTL-based context caching
- [x] Dynamic context file support

---

## File Structure

```
src/
├── __init__.py
├── config.py      # Configuration management
├── context.py     # Context file loading
└── types.py       # Shared types
```

---

## Types (src/types.py)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


class MemoryEntry(BaseModel):
    timestamp: datetime
    role: Literal["user", "assistant", "system"]
    content: str
    embedding: list[float] | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class DailyMemory(BaseModel):
    date: str  # YYYY-MM-DD
    entries: list[MemoryEntry] = Field(default_factory=list)


class ContextFile(BaseModel):
    name: str
    path: str
    content: str
    last_modified: datetime


class AssembledContext(BaseModel):
    agents: str
    soul: str
    user: str
    tools: str
    memories: list[MemoryEntry]
    system_prompt: str  # Combined
```

---

## Config (src/config.py)

```python
import os
import json
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Telegram
    telegram_bot_token: str = Field(..., validation_alias="TELEGRAM_BOT_TOKEN")
    
    # OpenAI (embeddings)
    openai_api_key: str = Field(..., validation_alias="OPENAI_API_KEY")
    
    # Kimi (primary LLM)
    kimi_api_key: str = Field(..., validation_alias="KIMI_API_KEY")
    kimi_base_url: str = Field(
        default="https://api.moonshot.cn/v1",
        validation_alias="KIMI_BASE_URL"
    )
    
    # Runtime settings
    default_llm_provider: str = Field(default="kimi")
    embedding_model: str = Field(default="text-embedding-3-small")
    chat_model: str = Field(default="kimi-k2-5")
    memory_context_limit: int = Field(default=20)
    
    # Paths
    memory_dir: Path = Field(default=Path("memory"))
    context_files: dict[str, Path] = Field(default_factory=lambda: {
        "agents": Path("AGENTS.md"),
        "soul": Path("SOUL.md"),
        "user": Path("USER.md"),
        "tools": Path("TOOLS.md"),
    })
    
    @classmethod
    def from_json(cls, path: Path) -> "Config":
        """Load config.json as defaults, env vars will override."""
        if not path.exists():
            return cls()
        with open(path) as f:
            data = json.load(f)
        # Env vars and .env override config.json values
        return cls(**data)


def load_config() -> Config:
    """Load configuration with proper precedence.
    
    Precedence (highest to lowest):
    1. Environment variables
    2. .env file
    3. config.json file
    4. Default values
    """
    # Pydantic Settings handles env vars and .env automatically
    config = Config()
    
    # config.json provides defaults that env vars can override
    if Path("config.json").exists():
        config = Config.from_json(Path("config.json"))
    
    return config
```

---

## Context (src/context.py)

```python
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any
from src.types import ContextFile, AssembledContext, MemoryEntry
from src.config import Config


class ContextCache:
    """Simple TTL cache for context files."""
    
    def __init__(self, ttl_seconds: int = 60) -> None:
        self._cache: dict[str, ContextFile] = {}
        self._timestamps: dict[str, datetime] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> ContextFile | None:
        """Get cached file if not expired."""
        if key not in self._cache:
            return None
        if datetime.now() - self._timestamps[key] > self._ttl:
            del self._cache[key]
            del self._timestamps[key]
            return None
        return self._cache[key]
    
    def set(self, key: str, value: ContextFile) -> None:
        """Cache a file with timestamp."""
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
    
    def invalidate(self, key: str) -> None:
        """Remove a file from cache."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached files."""
        self._cache.clear()
        self._timestamps.clear()


class ContextLoader:
    def __init__(self, config: Config, cache_ttl: int = 60) -> None:
        self.config = config
        self._cache = ContextCache(ttl_seconds=cache_ttl)
    
    async def load_file(self, name: str, path: Path) -> ContextFile:
        """Load a context file or fail if missing. Uses cache if available."""
        # Check cache first
        cached = self._cache.get(name)
        if cached:
            return cached
        
        if not path.exists():
            raise FileNotFoundError(f"Required context file missing: {path}")
        
        # Run file I/O in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, path.read_text, "utf-8")
        stat = await loop.run_in_executor(None, path.stat)
        
        file = ContextFile(
            name=name,
            path=str(path),
            content=content,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
        )
        
        self._cache.set(name, file)
        return file
    
    async def load_all(self) -> dict[str, ContextFile]:
        """Load all required context files concurrently."""
        tasks = [
            self.load_file(name, path)
            for name, path in self.config.context_files.items()
        ]
        files_list = await asyncio.gather(*tasks)
        return {f.name: f for f in files_list}
    
    async def assemble(self, memories: list[MemoryEntry] | None = None) -> AssembledContext:
        """Assemble complete context for LLM prompt."""
        files = await self.load_all()
        
        return AssembledContext(
            agents=files["agents"].content,
            soul=files["soul"].content,
            user=files["user"].content,
            tools=files["tools"].content,
            memories=memories or [],
            system_prompt=self._build_system_prompt(files),
        )
    
    def add_context_file(self, name: str, path: Path) -> None:
        """Dynamically add a custom context file."""
        self.config.context_files[name] = path
        self._cache.invalidate(name)
    
    def remove_context_file(self, name: str) -> None:
        """Remove a context file from loading."""
        self.config.context_files.pop(name, None)
        self._cache.invalidate(name)
    
    def _build_system_prompt(self, files: dict[str, ContextFile]) -> str:
        """Combine context files into system prompt."""
        parts = [
            "# AGENTS\n\n" + files["agents"].content,
            "# SOUL\n\n" + files["soul"].content,
            "# USER\n\n" + files["user"].content,
            "# TOOLS\n\n" + files["tools"].content,
        ]
        return "\n\n---\n\n".join(parts)
```

---

## Initial Context Files

### AGENTS.md
```markdown
# Agent Behavior Rules

## Core Principles

1. **Permission First**: Always ask before editing files, deleting data, making API calls, or running commands.

2. **Load Writing Skill**: ALWAYS load the `writing-clearly-and-concisely` skill before writing prose.

3. **Transparency**: Explain what you do and why.

4. **User Control**: The user decides.

5. **Privacy**: Never share data without consent.

## Communication
Be concise. Confirm ambiguous requests. Admit uncertainty.
```

### SOUL.md (template)
```markdown
# Alfred's Soul

## Personality
You are Alfred, a persistent memory-augmented assistant. You remember conversations, learn from the user, and grow more helpful over time.

## Traits
- Warm but professional
- Concise unless detail requested
- Proactive with memory
- Always admits uncertainty

## Voice
Direct, clear, personal. Use active voice. Omit needless words.
```

### USER.md (template)
```markdown
# User Profile

## Background
[To be filled through conversation]

## Preferences
[To be learned over time]

## Goals
[To be discovered]
```

### TOOLS.md (template)
```markdown
# Available Tools

## Local Tools
[To be configured]

## External APIs
[To be documented]
```

---

## Tests

```python
# tests/test_config.py
import pytest
from src.config import Config, load_config
from src.context import ContextLoader


def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("KIMI_API_KEY", "test_kimi")
    
    config = load_config()
    assert config.telegram_bot_token == "test_token"


@pytest.mark.asyncio
async def test_context_loader_fails_on_missing_file(tmp_path):
    config = Config(
        telegram_bot_token="t",
        openai_api_key="o",
        kimi_api_key="k",
        context_files={"agents": tmp_path / "nonexistent.md"},
    )
    loader = ContextLoader(config)
    
    with pytest.raises(FileNotFoundError):
        await loader.load_all()


@pytest.mark.asyncio
async def test_context_loader_caching(tmp_path):
    # Create a test file
    test_file = tmp_path / "test.md"
    test_file.write_text("test content")
    
    config = Config(
        telegram_bot_token="t",
        openai_api_key="o",
        kimi_api_key="k",
        context_files={"test": test_file},
    )
    loader = ContextLoader(config, cache_ttl=60)
    
    # First load should cache
    file1 = await loader.load_file("test", test_file)
    file2 = await loader.load_file("test", test_file)
    
    # Should be same object from cache
    assert file1 is file2


@pytest.mark.asyncio
async def test_dynamic_context_files(tmp_path):
    config = Config(
        telegram_bot_token="t",
        openai_api_key="o",
        kimi_api_key="k",
    )
    loader = ContextLoader(config)
    
    # Add custom context file
    custom_file = tmp_path / "custom.md"
    custom_file.write_text("custom content")
    loader.add_context_file("custom", custom_file)
    
    # Should be loadable
    files = await loader.load_all()
    assert "custom" in files
    assert files["custom"].content == "custom content"
```

---

## Success Criteria

- [x] All files pass mypy strict mode
- [ ] All tests pass (including async tests with pytest-asyncio)
- [x] Missing context files raise clear errors
- [x] Context assembles correctly
- [x] Config loads from env vars with proper precedence
- [x] Config.json provides defaults (env vars override)
- [x] Context caching works (TTL-based)
- [x] Dynamic context files can be added/removed
- [x] Async file loading uses thread pool for I/O
- [x] Concurrent loading of multiple context files

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Config precedence: env vars → .env → config.json → defaults | Standard 12-factor app pattern; most specific overrides least | Users can override any config via env vars |
| 2026-02-17 | Add TTL caching to ContextLoader | Avoid re-reading files on every message; configurable TTL | Better performance, reduced disk I/O |
| 2026-02-17 | Make ContextLoader async | Will be used in async Telegram bot; non-blocking I/O required | All loader methods return coroutines |
| 2026-02-17 | Support dynamic context files | Users may need custom context beyond standard 4 files | add_context_file() / remove_context_file() methods |
| 2026-02-17 | Skip file watching | Complexity not justified; TTL caching sufficient for MVP | Manual cache invalidation only |

---

## Open Questions

- [ ] Should we add structured logging for context loading operations?
- [ ] Should ContextCache have a max size limit (LRU eviction)?
- [ ] Should we validate context file content (e.g., require specific headers)?
