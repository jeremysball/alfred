# PRD: Alfred v1.0 - Complete Vision

## Overview

**Issue**: #48
**Status**: SUPERCEDED by docs/ROADMAP.md
**Priority**: High
**Created**: 2026-02-18
**Supersedes**: #10

> **Note**: This PRD has been superseded by `docs/ROADMAP.md` which now serves as the single source of truth for Alfred's vision, architecture, and roadmap. This file is kept for historical reference.

Alfred is a persistent memory-augmented LLM assistant. He remembers conversations across sessions, learns user preferences over time, and builds genuine understanding through accumulated context.

---

## Problem Statement

Existing LLM assistants start fresh every conversation. Users repeat themselves, lose context, and cannot build lasting relationships. Alfred solves this by maintaining persistent memory that grows richer over time.

---

## Solution Overview

### Core Concept
Alfred runs locally, speaks through Telegram or CLI, and uses a file-based memory system with vector embeddings for semantic retrieval.

### Key Differentiators
1. **Persistent Memory**: Every conversation stored with embeddings for semantic search
2. **Curated Knowledge**: MEMORY.md holds distilled, high-value insights
3. **Tool System**: Built-in tools for reading, writing, editing, and bash execution
4. **Streaming Agent Loop**: Real-time responses with tool execution visibility
5. **Model Agnostic**: Pluggable LLM providers (Kimi, OpenAI, etc.)
6. **File-Based Context**: Human-readable configuration (SOUL.md, USER.md, TOOLS.md)

---

## Design Principles

### 1. Model-Driven Intelligence
When Alfred makes decisions—what to remember, how to respond, which tool to use—the LLM decides. Prefer prompting over programming.

### 2. Zero-Command Interface
Users speak naturally. "What did we discuss about my project?" triggers semantic search automatically. No `/commands` required for core functionality.

### 3. Fail Fast
Errors surface immediately. Silent failures hide bugs. Memories without embeddings are rejected.

### 4. Streaming First
Users see responses in real-time. Tool execution happens visibly. No waiting for complete responses.

---

## Technical Architecture

### Technology Stack
- **Runtime**: Python 3.12+ with `uv`
- **Interfaces**: Telegram Bot API (async), CLI
- **Container**: Docker with Tailscale networking
- **Storage**: JSONL files with OpenAI embeddings
- **Search**: Cosine similarity on vector embeddings

### File Structure
```
alfred/
├── AGENTS.md              # Agent behavior rules
├── SOUL.md               # Alfred's personality
├── USER.md               # User preferences
├── TOOLS.md              # LLM/environment config
├── templates/            # Auto-created context templates
├── src/
│   ├── alfred.py         # Core engine
│   ├── agent.py          # Streaming agent loop
│   ├── llm.py            # Provider abstraction
│   ├── memory.py         # Memory store (JSONL + embeddings)
│   ├── session.py        # Session management
│   ├── context.py        # Context assembly
│   ├── embeddings.py     # OpenAI embeddings
│   ├── search.py         # Semantic search (messages + sessions)
│   ├── templates.py      # Template auto-creation
│   ├── cron/             # Cron jobs
│   │   └── session_summarizer.py  # Auto-summarize sessions
│   ├── tools/            # Tool implementations
│   │   ├── base.py       # Tool abstract class
│   │   ├── read.py       # File reading
│   │   ├── write.py      # File writing
│   │   ├── edit.py       # File editing
│   │   ├── bash.py       # Shell execution
│   │   ├── remember.py   # Save to memory
│   │   ├── search_memories.py    # Search individual messages
│   │   ├── search_sessions.py    # Search session summaries
│   │   ├── update_memory.py
│   │   └── forget.py     # Delete memories
│   └── interfaces/
│       ├── cli.py        # CLI interface
│       └── telegram.py   # Telegram bot
├── data/
│   ├── memories.jsonl           # Individual messages (with session_id)
│   └── session_summaries.jsonl  # Session summaries with embeddings
└── tests/
```

### Core Components

#### 1. Alfred Engine (`src/alfred.py`)
Orchestrates memory, context, LLM, and agent loop. Entry point for all interfaces.

#### 2. Agent Loop (`src/agent.py`)
Streaming agent that coordinates LLM and tool execution. Handles tool call parsing, execution, and result injection.

#### 3. Memory System (`src/memory.py`)
Dual embedding storage for granular and contextual retrieval:

**Message Store** (`data/memories.jsonl`)
- Individual messages with embeddings
- Tagged with `session_id` for grouping
- Semantic search for specific facts

**Session Summary Store** (`data/session_summaries.jsonl`)
- Auto-generated via cron (30 min idle or 20 messages)
- Embeddings for conversation-level search
- Captures narrative arc, not just facts

Supports:
- **Add**: Store messages with auto-generated embeddings
- **Search Messages**: Find specific facts via `search_memories`
- **Search Sessions**: Find conversation context via `search_sessions`
- **Update**: Modify content or importance
- **Delete**: Remove by ID or semantic query

#### 4. Tool System (`src/tools/`)
Pydantic-validated tools with automatic JSON schema generation:
- **ReadTool**: Read file contents
- **WriteTool**: Create or overwrite files
- **EditTool**: Surgical file edits
- **BashTool**: Execute shell commands
- **RememberTool**: Save memories
- **SearchMemoriesTool**: Semantic memory search
- **UpdateMemoryTool**: Modify existing memories
- **ForgetTool**: Delete memories

#### 5. Context Assembly (`src/context.py`)
Loads and assembles system prompt from:
- AGENTS.md (behavior rules)
- SOUL.md (personality)
- USER.md (user profile)
- TOOLS.md (available tools)
- Retrieved memories (top-k relevant)

---

## Memory Systems

### 1. Conversation Memory (Automatic)
Every interaction stored in `data/memories.jsonl` with:
- Timestamp, role, content
- OpenAI embedding vector
- `session_id` for grouping into conversations
- Importance score (0.0-1.0)

**Search:** `search_memories` tool for specific facts, commands, precise details.

### 2. Session Summaries (Cron-Generated)
Auto-generated via cron job after 30 minutes of inactivity or 20 new messages:
- Stored in `data/session_summaries.jsonl`
- LLM-generated narrative summary
- Separate embedding for conversation-level search
- Versioned (replaced on re-summarization, not appended)

**Search:** `search_sessions` tool for themes, projects, conversation arcs.

### 3. Dual Semantic Retrieval
Query compared against both indexes:
- **Messages:** Cosine similarity on individual memories
- **Sessions:** Cosine similarity on summaries

Two separate tools; Alfred chooses based on query intent.

---

## Roadmap to v1.0

| # | Milestone | Status | Description |
|---|-----------|--------|-------------|
| M1 | Project Setup | ✅ Done | Repository, tooling, CI/CD |
| M2 | Core Infrastructure | ✅ Done | Config, context, templates |
| M3 | Memory Foundation | ✅ Done | JSONL storage, embeddings |
| M4 | Vector Search | ✅ Done | Semantic retrieval |
| M5 | Interfaces | ✅ Done | CLI + Telegram |
| M6 | Kimi Provider | ✅ Done | Moonshot AI integration |
| M7 | Tool System | ✅ Done | Built-in tools with schemas |
| M8 | Agent Loop | ✅ Done | Streaming with tool execution |
| M9 | Distillation | 🔲 Todo | Auto-extract insights to MEMORY.md |
| M10 | Learning | 🔲 Todo | Auto-update USER.md from patterns |
| M11 | Compaction | 🔲 Todo | Summarize long conversations |
| M12 | Testing | 🔲 Todo | Comprehensive test coverage |
| M13 | Documentation | 🔲 Todo | API docs, architecture guide |

---

## Success Criteria

- [ ] Alfred recalls conversations from any prior session
- [ ] Semantic search returns >80% relevant results
- [ ] Response latency under 5 seconds (streaming start)
- [ ] Zero data loss across restarts
- [ ] All tests passing with >80% coverage
- [ ] Documentation complete for contributors

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
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `python-telegram-bot` | Telegram Bot API |
| `openai` | Embeddings |
| `httpx` | HTTP client for LLM providers |
| `pydantic` | Data validation |
| `aiofiles` | Async file operations |
| `python-dotenv` | Environment loading |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-17 | JSONL over per-day files | Simpler, unified search, easier CRUD |
| 2026-02-17 | MEMORY.md over IMPORTANT.md | Matches OpenClaw pattern |
| 2026-02-17 | Single user, single agent | MVP simplicity |
| 2026-02-18 | Tool system with Pydantic | Automatic schema generation, validation |
| 2026-02-18 | Streaming agent loop | Real-time feedback, better UX |

---

## Notes

- Keep all memories forever (no automatic pruning)
- No encryption at rest (for now)
- Local development with Docker Compose
- Pre-commit hooks for code quality
