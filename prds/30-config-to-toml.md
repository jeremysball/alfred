# PRD: Migrate config.json to alfred.toml

## Overview

**Issue**: #30
**Parent**: #10 (Alfred - The Rememberer)
**Status**: Planning
**Priority**: Low
**Created**: 2026-02-17

Replace JSON configuration with TOML for better readability, usability, and comment support.

---

## Problem Statement

JSON config files have several drawbacks:
- No comments (can't document fields inline)
- Strict syntax (trailing commas, quoting everything)
- Harder for humans to read and edit
- No clear visual hierarchy for nested structures

TOML addresses these while remaining simple and widely supported.

---

## Solution

1. Rename `config.json` → `alfred.toml`
2. Convert current config to TOML format
3. Swap JSON parsing for TOML in `src/config.py`
4. Add high-quality inline comments where they add value
5. Keep minimal structure (no verbose documentation)

---

## Acceptance Criteria

- [ ] `config.json` removed, `alfred.toml` created
- [ ] `src/config.py` loads from TOML
- [ ] Precedence unchanged: env vars → .env → alfred.toml
- [ ] Config class unchanged (same fields, same validation)
- [ ] `.gitignore` updated (alfred.toml or keep in repo?)
- [ ] Tests updated

---

## Current Config (JSON)

```json
{
  "default_llm_provider": "kimi",
  "embedding_model": "text-embedding-3-small",
  "chat_model": "kimi-k2-5",
  "memory_context_limit": 20,
  "workspace_dir": "data",
  "memory_dir": "data/memory",
  "context_files": {
    "agents": "data/AGENTS.md",
    "soul": "data/SOUL.md",
    "user": "data/USER.md",
    "tools": "data/TOOLS.md"
  }
}
```

---

## New Config (TOML)

Generated on first run to `/app/alfred.toml`:

```toml
# Alfred Configuration
# Environment variables override these settings (see .env.example)

# LLM Provider Settings
default_llm_provider = "kimi"
embedding_model = "text-embedding-3-small"
chat_model = "kimi-k2-5"
memory_context_limit = 20

# Paths
workspace_dir = "data"
memory_dir = "data/memory"

# Context files loaded on each conversation
[context_files]
agents = "data/AGENTS.md"
soul = "data/SOUL.md"
user = "data/USER.md"
tools = "data/TOOLS.md"
```

---

## Code Changes (src/config.py)

```python
"""Configuration management for Alfred."""

import tomllib  # Python 3.11+
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram (required - no default)
    telegram_bot_token: str = Field(..., validation_alias="TELEGRAM_BOT_TOKEN")

    # OpenAI (required - no default)
    openai_api_key: str = Field(..., validation_alias="OPENAI_API_KEY")

    # Kimi (required - no defaults)
    kimi_api_key: str = Field(..., validation_alias="KIMI_API_KEY")
    kimi_base_url: str = Field(..., validation_alias="KIMI_BASE_URL")

    # Runtime settings (no defaults - from alfred.toml)
    default_llm_provider: str
    embedding_model: str
    chat_model: str
    memory_context_limit: int
    workspace_dir: Path
    memory_dir: Path
    context_files: dict[str, Path]


def load_config(config_path: Path = Path("/app/alfred.toml")) -> Config:
    """Load configuration with alfred.toml as source of truth.

    Config is generated on first run if missing.

    Precedence (highest to lowest):
    1. Environment variables
    2. .env file
    3. /app/alfred.toml file
    """
    if not config_path.exists():
        _generate_default_config(config_path)

    with open(config_path, "rb") as f:
        base_config = tomllib.load(f)

    # Pydantic merges: env vars override base_config values
    return Config(**base_config)


def _generate_default_config(path: Path) -> None:
    """Generate default alfred.toml config file."""
    default_config = """# Alfred Configuration
# Environment variables override these settings (see .env.example)

# LLM Provider Settings
default_llm_provider = "kimi"
embedding_model = "text-embedding-3-small"
chat_model = "kimi-k2-5"
memory_context_limit = 20

# Paths
workspace_dir = "data"
memory_dir = "data/memory"

# Context files loaded on each conversation
[context_files]
agents = "data/AGENTS.md"
soul = "data/SOUL.md"
user = "data/USER.md"
tools = "data/TOOLS.md"
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(default_config)
```

---

## Dependencies

Python 3.11+ includes `tomllib` in stdlib. No new dependencies needed.

If Python < 3.11 support is required, add `tomli` as a dependency.

---

## Milestones

- [ ] **M1: Create alfred.toml** - Convert config.json to TOML format with comments
- [ ] **M2: Update config.py** - Swap JSON parsing for TOML
- [ ] **M3: Clean up** - Remove config.json, update tests

---

## Success Criteria

- [ ] `alfred.toml` exists with current config values
- [ ] Config loads successfully from `/app/alfred.toml`
- [ ] Config auto-generated on first run if missing
- [ ] Env vars still override TOML values
- [ ] All existing tests pass
- [ ] No behavior changes (just format swap)

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Use `alfred.toml` (not `config.toml`) | More descriptive, project-specific | Clearer purpose |
| 2026-02-17 | No migration script | No existing users | Simpler implementation |
| 2026-02-17 | Minimal comments | Keep file clean | Not overwhelming |
| 2026-02-17 | Use stdlib `tomllib` | Python 3.11+ already required | No new dependencies |
| 2026-02-17 | Generate config on first run | Clean initial setup | No committed config file |
| 2026-02-17 | Place in `/app/alfred.toml` | Consistent with Docker layout | Clear location |
