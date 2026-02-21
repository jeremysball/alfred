# Alfred Architecture

## Overview

Alfred is a persistent memory-augmented LLM assistant. He maintains conversation history, learns user preferences, and brings relevant context into every interaction.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Telegram Bot                        │
│                   (Single User Interface)                   │
│              Each thread = fresh session                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Config     │  │   Context    │  │    Memory    │      │
│  │   Manager    │  │   Loader     │  │    Store     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLM Provider Layer                     │
│         ┌──────────────┐          ┌──────────────┐         │
│         │    Kimi      │          │   OpenAI     │         │
│         │   Provider   │          │  (Future)    │         │
│         └──────────────┘          └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules

### 1. Configuration (`src/config.py`)

Manages application settings with environment variable override.

**Key Features:**
- Pydantic-based validation
- Hierarchical config: `config.json` → `.env` → environment variables
- Type-safe settings access

**Configuration Sources (precedence high to low):**
1. Environment variables
2. `.env` file
3. `config.json` file (source of truth for defaults)

### 2. Context Management (`src/context.py`)

Loads and assembles context files for LLM prompts.

**Components:**
- `ContextCache`: TTL-based file caching (60 second default)
- `ContextLoader`: Async file loading with concurrent operations
- `AssembledContext`: Combined prompt ready for LLM

**Context Files:**
| File | Purpose |
|------|---------|
| `data/AGENTS.md` | Agent behavior rules and instructions |
| `data/SOUL.md` | Personality, voice, and identity definition |
| `data/USER.md` | User preferences and patterns |
| `data/TOOLS.md` | Available tools and usage guidelines |
| `MEMORY.md` | Curated long-term memory |

### Template System

Alfred uses templates for initial context files. On first run, templates are copied from `templates/` to `data/` if they don't exist.

```
templates/               # Built-in templates (read-only)
├── AGENTS.md
├── SOUL.md
├── USER.md
├── TOOLS.md
└── MEMORY.md

data/                    # User's runtime files
├── AGENTS.md            # Copied from template if missing
├── SOUL.md
├── USER.md
├── TOOLS.md
├── MEMORY.md
└── memory/              # JSONL memory storage
    └── memories.jsonl
```

**Behavior:**
- Alfred checks for missing context files on startup
- Missing files are auto-created from templates
- User modifications persist; templates don't overwrite

**Data Flow:**
```
config.json ──► ContextLoader ──► ContextCache ──► AssembledContext
                                    │
                    File changes ──►┘ (invalidates cache)
```

### 3. LLM Provider (`src/llm.py`)

Abstracts LLM interactions with retry logic and error handling.

**Architecture:**
```
LLMProvider (ABC)
    ├── KimiProvider (implemented)
    └── OpenAIProvider (future)
```

**Key Features:**
- Exponential backoff with jitter for retries
- Structured error types: `RateLimitError`, `APIError`, `TimeoutError`
- Streaming and non-streaming chat interfaces
- Comprehensive logging

**Retry Behavior:**
- 3 max retries with exponential backoff
- Base delay: 1s, max delay: 60s
- Jitter: 0.5x to 1.5x randomization
- No retry on programming errors (ValueError, TypeError)

### 4. Type System (`src/types.py`)

Pydantic models for type safety across the application.

**Core Types:**
- `MemoryEntry`: Single memory with embedding and metadata
- `ContextFile`: Loaded file with metadata
- `AssembledContext`: Complete prompt context

## Data Flow

### Message Processing

```
1. User Message
        │
        ▼
2. ContextLoader.assemble()
   - Load AGENTS.md, SOUL.md, USER.md, TOOLS.md
   - Retrieve relevant memories
   - Build system prompt
        │
        ▼
3. LLMProvider.chat()
   - Send to configured LLM (Kimi)
   - Retry on transient failures
        │
        ▼
4. Store Response
   - Save to memory store with embedding
        │
        ▼
5. Reply to User
```

### Memory Storage

Alfred uses a three-layer memory architecture:

```
data/
├── memory/
│   └── memories.jsonl      # Layer 1: Curated facts (via remember tool)
│
└── sessions/
    └── {session_id}/
        ├── messages.jsonl  # Layer 3: Session messages with embeddings
        └── summary.json    # Layer 2: Session summary + embedding
```

**Layer 1: Curated Memory** (`data/memory/memories.jsonl`)
- Facts Alfred explicitly remembers via `remember` tool
- Has embeddings for semantic search
- Can link to sessions via optional `session_id` field

**Layer 2: Session Summaries** (`data/sessions/{id}/summary.json`)
- LLM-generated narrative summaries of conversations
- Auto-created via cron job (30 min idle or 20 messages)
- Has embeddings for semantic search

**Layer 3: Session Messages** (`data/sessions/{id}/messages.jsonl`)
- Raw conversation messages
- Each message has embedding for contextual search
- Enables "hyperweb retrieval": find session first, then search within

Each memory entry contains:
- Timestamp, role, content
- OpenAI embedding vector
- Entry ID for CRUD operations
- Optional session_id for linking

## Error Handling Strategy

| Layer | Strategy | Behavior |
|-------|----------|----------|
| Config | Validation | Fail fast on missing required values |
| Context | Fail fast | Raise on missing required files |
| LLM | Retry + fallback | Exponential backoff, then error |
| Memory | Graceful degradation | Log and continue on storage errors |

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| Configuration | Pydantic Settings |
| Async Runtime | asyncio |
| HTTP Client | aiohttp |
| LLM Client | OpenAI SDK |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio |
| Linting | ruff |
| Type Checking | mypy (strict) |

## Design Principles

1. **Fail Fast**: Configuration and context errors fail immediately
2. **Async First**: All I/O operations are async
3. **Type Safety**: Strict mypy, Pydantic models throughout
4. **Observability**: Structured logging at all layers
5. **Modularity**: Clear interfaces, swappable implementations

## Alfred Design Philosophies

### Model-Driven Decisions

When making decisions—what to remember, when to summarize, how to respond—prefer prompting over programming. Let the LLM decide:
- What deserves recording to memory
- When context grows too long
- How to structure responses
- What matters in a conversation

### Memory Behavior

- **Curated Memory**: Alfred autonomously decides what to remember using the `remember` tool, storing curated facts to `data/memory/memories.jsonl`
- **Session Storage**: Conversations stored in `data/sessions/{session_id}/` with messages and auto-generated summaries (PRD #76)
- **Contextual Retrieval**: PRD #77 enables searching within relevant sessions for higher precision

## Related Documentation

- [API Reference](API.md) — Module documentation
- [Deployment](DEPLOYMENT.md) — Production setup
- [Cron Jobs](cron-jobs.md) — Scheduled tasks
- [Roadmap](ROADMAP.md) — Development progress
