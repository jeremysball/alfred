# PRD: Alfred v1.0 - Complete Vision

## Overview

**Issue**: #48
**Status**: PERMANENT
**Priority**: High
**Created**: 2026-02-18
**Supersedes**: #10

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
├── MEMORY.md             # Curated long-term memory
├── templates/            # Auto-created context templates
├── src/
│   ├── alfred.py         # Core engine
│   ├── agent.py          # Streaming agent loop
│   ├── llm.py            # Provider abstraction
│   ├── memory.py         # Memory store (JSONL + embeddings)
│   ├── context.py        # Context assembly
│   ├── embeddings.py     # OpenAI embeddings
│   ├── search.py         # Semantic search
│   ├── templates.py      # Template auto-creation
│   ├── tools/            # Tool implementations
│   │   ├── base.py       # Tool abstract class
│   │   ├── read.py       # File reading
│   │   ├── write.py      # File writing
│   │   ├── edit.py       # File editing
│   │   ├── bash.py       # Shell execution
│   │   ├── remember.py   # Save to memory
│   │   ├── search_memories.py
│   │   ├── update_memory.py
│   │   └── forget.py     # Delete memories
│   └── interfaces/
│       ├── cli.py        # CLI interface
│       └── telegram.py   # Telegram bot
├── data/
│   └── memories.jsonl    # Unified memory store
└── tests/
```

### Core Components

#### 1. Alfred Engine (`src/alfred.py`)
Orchestrates memory, context, LLM, and agent loop. Entry point for all interfaces.

#### 2. Agent Loop (`src/agent.py`)
Streaming agent that coordinates LLM and tool execution. Handles tool call parsing, execution, and result injection.

#### 3. Memory System (`src/memory.py`)
Unified JSONL storage with embeddings. Supports:
- **Add**: Store new memories with auto-generated embeddings
- **Search**: Semantic search by similarity × importance
- **Update**: Modify content or importance
- **Delete**: Remove by ID or semantic query
- **Curated**: Read/write MEMORY.md for long-term knowledge

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
- Importance score (0.0-1.0)
- Tags for categorization

### 2. Curated Memory (MEMORY.md)
High-value knowledge manually or automatically distilled. Loaded into every context.

### 3. Semantic Retrieval
Query embedding compared against all memory embeddings. Results ranked by:
```
score = cosine_similarity × (0.7 + 0.3 × importance)
```

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
