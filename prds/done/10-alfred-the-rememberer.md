# PRD: Alfred - The Rememberer LLM Assistant

## Overview

**Issue**: #10  
**Status**: Superseded by [#48](48-alfred-v1-vision.md)  
**Priority**: High  
**Created**: 2026-02-16

> **⚠️ Deprecated**: This PRD has been superseded by [PRD 48: Alfred v1.0 - Complete Vision](48-alfred-v1-vision.md). Please refer to PRD 48 for the current architecture and roadmap.

Alfred maintains context across infinite time horizons. Unlike assistants that start fresh each conversation, Alfred captures daily interactions, curates long-term memories with embeddings, and evolves its understanding of the user.

---

## Problem Statement

Current LLM assistants have no long-term memory. Users lose context, repeat explanations, and cannot build lasting relationships with their assistants. Alfred solves this by remembering everything from day one.

---

## Solution Overview

### Core Concept
Alfred lives in a Docker container, speaks through Telegram, and uses a file-based memory system with vector embeddings.

### Key Differentiators
1. **Infinite Memory**: Markdown storage with OpenAI embeddings for semantic retrieval
2. **Daily Capture**: Automatic logging to dated Markdown files
3. **Curated Memory**: MEMORY.md holds refined, persistent knowledge
4. **Automatic Context**: Relevant memories load without user commands
5. **Modular Providers**: Pluggable LLM support (starts with Kimi)
6. **File-Based Config**: Human-readable context files
7. **Template System**: Auto-creates context files from bundled templates

---

## Design Principles

### 1. Model-Driven Over Code
When Alfred needs to make decisions—what to remember, when to summarize, how to respond—use the LLM. Prefer prompting over programming. The model decides when to write to USER.md, when a memory matters, when context grows too long.

### 2. Zero-Command Interface
Never require users to run commands. Alfred responds to natural language. "Remember when we talked about my Python project?" triggers semantic search automatically. No `/search` commands. No manual memory management.

### 3. Fail Fast
Errors surface immediately. Silent failures hide bugs.

---

## Technical Architecture

### Technology Stack
- **Runtime**: Python with `uv`
- **Interface**: Telegram Bot API (async)
- **Container**: Docker
- **Storage**: JSON files + OpenAI embeddings
- **Search**: Cosine similarity on embeddings
- **Config**: Environment variables + `.env` files

### File Structure
```
alfred/
├── AGENTS.md              # Behavior rules for ALL agents
├── SOUL.md               # Alfred's personality (includes identity)
├── USER.md               # User preferences
├── TOOLS.md              # Local tool configs
├── MEMORY.md             # Curated long-term memory
├── templates/            # Bundled templates (copied to /app/templates)
│   ├── SOUL.md
│   ├── USER.md
│   ├── TOOLS.md
│   └── MEMORY.md
├── CAPABILITIES/         # Capability implementations
│   ├── __init__.py
│   ├── search.py
│   └── remember.py
├── memory/               # Daily memory captures (Markdown)
│   ├── 2026-02-16.md
│   ├── 2026-02-17.md
│   └── ...
├── config.json           # Runtime config
├── .env                  # Secrets (gitignored)
└── src/
    ├── __init__.py
    ├── bot.py            # Telegram handler
    ├── memory.py         # Memory CRUD
    ├── embeddings.py     # OpenAI embeddings
    ├── llm.py            # Provider abstraction
    ├── context.py        # Context assembly
    ├── templates.py      # Template auto-creation
    ├── capabilities.py   # Capability registry
    ├── compaction.py     # Long context management
    ├── distillation.py   # Memory file writing
    └── learning.py       # Agent file updates
```

### Data Schema

#### Daily Memory (Markdown)
Human-readable daily logs stored as Markdown files:

```markdown
# 2026-02-16

## 14:32 - User
I'm starting a new Python project

## 14:33 - Assistant
That's exciting! What are you building?

<!-- metadata: {"importance": 0.8, "tags": ["coding", "python"]} -->
```

#### MEMORY.md (Curated Long-Term)
Distilled knowledge that persists across sessions. Model-driven updates.

---

## Memory Systems

### 1. Daily Memory (Automatic)
Every interaction stores to `memory/YYYY-MM-DD.md` (Markdown) with embeddings.

### 2. MEMORY.md (Curated)
High-value memories live here. Alfred suggests additions; users confirm or the model decides.

### 3. Compaction (Manual)
Long conversations grow unwieldy. The `/compact` command triggers intelligent summarization. Alfred uses the model to decide what matters, what to truncate, how to summarize.

### 4. Distillation (Automatic)
Alfred extracts insights from conversations and writes to memory files. Model-driven: the LLM decides what deserves recording.

### 5. Learning (Automatic)
Alfred updates agent files (USER.md, SOUL.md) based on observed patterns. Model-driven decisions about what to learn and record.

### 6. Session-Based Architecture
Each Telegram thread/conversation starts fresh. Files are Alfred's persistence layer. Sessions load context from files, not from previous session state.

---

## Context System

### Loaded on Every Message
1. **AGENTS.md** - Universal behavior
2. **SOUL.md** - Personality
3. **USER.md** - User profile
4. **TOOLS.md** - Available tools
5. **Retrieved Memories** - Top-k relevant via semantic search

### Memory Retrieval Flow
```
User Message → Embed → Search All Memories (cosine similarity)
→ Rank by relevance + recency + importance
→ Top 10-20 memories → Inject into context → Send to LLM
```

---

## Milestone Roadmap

| # | Milestone | Issue | Description |
|---|-----------|-------|-------------|
| 1 | Project Setup | #11 | pyproject.toml, uv, mypy, ruff, pre-commit, assets |
| 2 | Core Infrastructure | #12 | Config, file loaders, context system |
| 3 | Memory Foundation | #13 | Markdown storage, OpenAI embeddings |
| 4 | Vector Search | #14 | Semantic retrieval, context injection |
| 5 | Telegram Bot | #15 | Async bot handler |
| 6 | Kimi Provider | #16 | First LLM provider |
| 7 | Personality | #17 | SOUL.md/USER.md injection |
| 8 | Capabilities | #18 | Automatic model-driven actions |
| 9 | Compaction | #19 | Long context summarization |
| 10 | Distillation | #20 | Writing to memory files |
| 11 | Learning | #21 | Writing to agent files |
| 12 | Testing | #22 | pytest, mypy, integration tests |

---

## AGENTS.md Template

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

---

## Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN=xxx
OPENAI_API_KEY=xxx
KIMI_API_KEY=xxx
KIMI_BASE_URL=https://api.moonshot.cn/v1

# Optional
DEFAULT_LLM_PROVIDER=kimi
MEMORY_CONTEXT_LIMIT=20
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=kimi-k2-5
```

---

## Success Criteria

- Alfred recalls conversations from months ago
- Context loads automatically without commands
- Personality stays consistent
- Response latency under 5 seconds
- Zero data loss across restarts
- Retrieved memories exceed 80% relevance

---

## Dependencies

See individual milestone PRDs for specific dependencies.

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Memory files are Markdown, not JSON | Human-readable, matches OpenClaw pattern | M3 implementation |
| 2026-02-17 | Long-term memory is MEMORY.md, not IMPORTANT.md | Matches OpenClaw pattern | Context loader, Docker setup |
| 2026-02-17 | Single user, single agent | MVP simplicity | Architecture, Telegram bot |
| 2026-02-17 | Session-based (each thread = fresh start) | Clean context per conversation | Memory loading strategy |
| 2026-02-17 | IDENTITY.md merged into SOUL.md | Simpler structure | Fewer context files |

---

## Notes

- Keep all memories forever (no pruning)
- No encryption at rest (for now)
- Local development with provided Docker Compose
- Use real API calls in integration tests
- Use golden vectors to avoid re-embedding costs
