# Alfred Architecture

## Overview

Alfred is a persistent memory-augmented LLM assistant. He maintains conversation history, learns user preferences, and brings relevant context into every interaction.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Telegram Bot                        │
│                   (Multi-user Interface)                    │
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
| `AGENTS.md` | Agent behavior rules and instructions |
| `SOUL.md` | Personality and voice definition |
| `USER.md` | User preferences and patterns |
| `TOOLS.md` | Available tools and usage guidelines |

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
- `DailyMemory`: Day-grouped memories
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
   - Save to memory store
   - Update user model
        │
        ▼
5. Reply to User
```

### Memory Storage

**Current (M2):** File-based JSON storage
```
memory/
└── 2026-02-17.json      # Daily memory files
└── 2026-02-16.json
```

**Future (M4):** Vector search with embeddings
```
memory/
├── embeddings/          # Vector index
└── archive/             # Compacted summaries
```

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

## Future Architecture (PRD Roadmap)

### M3: Memory Foundation
- Persistent conversation storage
- Daily memory files with JSON format

### M4: Vector Search
- Embedding-based semantic search
- FAISS or similar vector store

### M5: Telegram Bot
- Multi-user support
- Message handlers and commands

### M6: Kimi Provider ✅
- Moonshot AI integration
- Retry logic with backoff

### M7+: Advanced Features
- Personality modeling
- Capability system
- Memory compaction
- Knowledge distillation
