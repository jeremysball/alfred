# PRD: M2 - Core Infrastructure

## Overview

**Issue**: #12  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #11 (M1: Project Setup)  
**Status**: Planning  
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

- [ ] `src/config.py` - Configuration dataclass with validation
- [ ] `src/context.py` - Context file loader and assembler
- [ ] `src/types.py` - Shared type definitions (Pydantic models)
- [ ] Load AGENTS.md, SOUL.md, USER.md, TOOLS.md
- [ ] Environment variable support with `.env` loading
- [ ] `config.json` override support
- [ ] Fail on missing required files
- [ ] Type-safe throughout (mypy strict passes)

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
        """Load config.json overrides."""
        if not path.exists():
            return cls()
        with open(path) as f:
            data = json.load(f)
        return cls(**data)


def load_config() -> Config:
    """Load configuration from env and optional config.json."""
    config = Config()
    if Path("config.json").exists():
        config = Config.from_json(Path("config.json"))
    return config
```

---

## Context (src/context.py)

```python
from pathlib import Path
from datetime import datetime
from src.types import ContextFile, AssembledContext
from src.config import Config


class ContextLoader:
    def __init__(self, config: Config) -> None:
        self.config = config
    
    def load_file(self, name: str, path: Path) -> ContextFile:
        """Load a context file or fail if missing."""
        if not path.exists():
            raise FileNotFoundError(f"Required context file missing: {path}")
        
        content = path.read_text(encoding="utf-8")
        stat = path.stat()
        
        return ContextFile(
            name=name,
            path=str(path),
            content=content,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
        )
    
    def load_all(self) -> dict[str, ContextFile]:
        """Load all required context files."""
        files = {}
        for name, path in self.config.context_files.items():
            files[name] = self.load_file(name, path)
        return files
    
    def assemble(self, memories: list = None) -> AssembledContext:
        """Assemble complete context for LLM prompt."""
        files = self.load_all()
        
        return AssembledContext(
            agents=files["agents"].content,
            soul=files["soul"].content,
            user=files["user"].content,
            tools=files["tools"].content,
            memories=memories or [],
            system_prompt=self._build_system_prompt(files),
        )
    
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


def test_context_loader_fails_on_missing_file(tmp_path):
    config = Config(
        telegram_bot_token="t",
        openai_api_key="o",
        kimi_api_key="k",
        context_files={"agents": tmp_path / "nonexistent.md"},
    )
    loader = ContextLoader(config)
    
    with pytest.raises(FileNotFoundError):
        loader.load_all()
```

---

## Success Criteria

- [ ] All files pass mypy strict mode
- [ ] All tests pass
- [ ] Missing context files raise clear errors
- [ ] Context assembles correctly
- [ ] Config loads from env vars
- [ ] Config.json overrides work
