# Alfred - The Rememberer

**A persistent memory-augmented LLM assistant that remembers conversations across sessions, learns user preferences over time, and builds genuine understanding through accumulated context.**

---

## Vision

Existing LLM assistants start fresh every conversation. Users repeat themselves, lose context, and cannot build lasting relationships. Alfred solves this by maintaining persistent memory that grows richer over time.

**Core concept:** Alfred runs locally, speaks through Telegram or CLI, and uses a file-based memory system with dual vector embeddings for semantic retrieval.

---

## Design Principles

1. **Model-Driven Intelligence** — When Alfred makes decisions—what to remember, how to respond, which tool to use—the LLM decides. Prefer prompting over programming.

2. **Zero-Command Interface** — Users speak naturally. "What did we discuss about my project?" triggers semantic search automatically. No `/commands` required for core functionality.

3. **Fail Fast** — Errors surface immediately. Silent failures hide bugs. Memories without embeddings are rejected.

4. **Streaming First** — Users see responses in real-time. Tool execution happens visibly. No waiting for complete responses.

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
├── templates/            # Context templates (copied to data/ on first run)
│   ├── AGENTS.md
│   ├── SOUL.md
│   ├── USER.md
│   ├── TOOLS.md
│   └── MEMORY.md
├── src/
│   ├── alfred.py         # Core engine
│   ├── agent.py          # Streaming agent loop
│   ├── llm.py            # Provider abstraction (Kimi)
│   ├── memory.py         # Memory store (JSONL + embeddings)
│   ├── session.py        # Session management
│   ├── context.py        # Context assembly
│   ├── embeddings.py     # OpenAI embeddings
│   ├── search.py         # Semantic search
│   ├── templates.py      # Template auto-creation
│   ├── cron/             # Cron jobs
│   │   ├── scheduler.py
│   │   ├── executor.py
│   │   ├── store.py
│   │   └── notifier.py
│   ├── tools/            # Tool implementations
│   │   ├── base.py       # Tool abstract class
│   │   ├── read.py       # File reading
│   │   ├── write.py      # File writing
│   │   ├── edit.py       # File editing
│   │   ├── bash.py       # Shell execution
│   │   ├── remember.py   # Save to memory
│   │   ├── search_memories.py
│   │   ├── update_memory.py
│   │   ├── forget.py     # Delete memories
│   │   ├── schedule_job.py
│   │   ├── list_jobs.py
│   │   ├── approve_job.py
│   │   └── reject_job.py
│   └── interfaces/
│       ├── cli.py        # CLI interface
│       └── telegram.py   # Telegram bot
├── data/
│   ├── memory/
│   │   └── memories.jsonl    # Curated facts with embeddings
│   ├── sessions/             # Session storage (PRD #76)
│   │   └── {session_id}/
│   │       ├── messages.jsonl    # Session messages with embeddings
│   │       └── summary.json      # Session summary + embedding
│   ├── cron.jsonl            # Scheduled jobs
│   ├── cron_history.jsonl    # Job execution history
│   ├── cron_logs.jsonl       # Job output logs
│   ├── AGENTS.md             # Agent behavior rules
│   ├── SOUL.md               # Alfred's personality
│   ├── USER.md               # User preferences
│   └── TOOLS.md              # Tool definitions
└── tests/
```

---

## Memory Systems

Alfred uses a three-layer memory architecture:

```
data/
├── memory/
│   └── memories.jsonl      # Layer 1: Curated facts
│
└── sessions/
    └── {session_id}/
        ├── messages.jsonl  # Layer 3: Session messages
        └── summary.json    # Layer 2: Session summary
```

### Layer 1: Curated Memory (Implemented)
Facts Alfred explicitly remembers:
- Alfred uses `remember` tool to store important information
- Stored in `data/memory/memories.jsonl` with embeddings
- Semantic search via `search_memories` tool
- Full CRUD: create, read, update, delete operations
- Can link to sessions via optional `session_id` field

### Layer 2: Session Summaries (PRD #76)
Narrative summaries of conversations:
- Auto-generated via cron (30 min idle or 20 messages)
- Stored in `data/sessions/{session_id}/summary.json`
- Has embedding for semantic search
- Enables finding past conversations by theme

### Layer 3: Session Messages (PRD #77)
Individual messages within sessions:
- Stored in `data/sessions/{session_id}/messages.jsonl`
- Each message has embedding
- Enables contextual narrowing: find session first, then search within

### Session History (In-Memory)
Current conversation context:
- Stored in `SessionManager` singleton during active session
- Injected into every LLM call for multi-turn conversation
- Persisted to session folders (PRD #76)

### Curated Memory (MEMORY.md)
Manually curated long-term insights:
- Loaded into every context
- Edited directly or via prompts

See PRDs #76 and #77 for contextual retrieval details.

---

## Roadmap

### Completed ✅

| Milestone | Description |
|-----------|-------------|
| M1 | Project Setup - Repository structure, tooling, CI/CD |
| M2 | Core Infrastructure - Configuration, context loading, prompt assembly |
| M3 | Memory Foundation - JSONL storage with embeddings |
| M4 | Vector Search - Semantic memory retrieval |
| M5 | Telegram Bot - Multi-user chat interface with CLI |
| M6 | Kimi Provider - Integration with Moonshot AI's Kimi API |
| M7 | Personality & Context - SOUL.md, USER.md, context assembly |
| M8 | Tool System - Built-in tools with Pydantic schemas |
| M9 | Agent Loop - Streaming with tool execution |
| M10 | Memory System V2 - Full CRUD operations |
| M11 | PyPI Trusted Publishing - Automated package distribution |
| M12 | Rich Markdown Output - Streaming markdown rendering with Rich Live for CLI |

### In Progress / Next Up 🔨

| # | Milestone | Description |
|---|-----------|-------------|
| 12 | Session Summarization | Cron-based auto-summarization (30 min idle or 20 messages) |
| 13 | Learning System | Prompt-based learning to update USER.md/SOUL.md |
| 14 | Cron Error Handling & UX | Friendly errors, local timezone, CLI responsiveness |
| 15 | README Landing Page | Transform README into compelling OSS landing page |

### Short-term 📋

| # | Milestone | Description |
|---|-----------|-------------|
| 17 | Testing & Quality | Comprehensive test coverage, fix deprecation warnings |
| 18 | Edit Tool Safety | Exact text matching validation, pre-edit verification |
| 19 | Test Configuration | Skip integration/e2e by default, separate CI jobs |
| 20 | Type Safety | Fix Tool class type safety, complete type annotations |
| 21 | Code Quality | Auto-fix Ruff violations, manual lint fixes |

### Medium-term 📅

| # | Milestone | Description |
|---|-----------|-------------|
| 22 | Advanced Session Features | LLM context control, substring search, on-demand summaries |
| 23 | Contextual Retrieval System | Triple-layer memory: global + session summaries + per-session message embeddings (PRD #77) |
| 24 | Configurable Context Budget | User-defined context percentages: 50% conversation, 10% tools, etc. |
| 25 | Local Embedding Models | Support for MiniLM, Nomic, MPNet running locally (no API calls) |
| 26 | HTTP API + Cron | Local API for scheduled actions |
| 27 | Config TOML Migration | Replace config.json with alfred.toml |
| 28 | Observability & Logging | Structured logging, tracing, metrics |

### Long-term 🔮

| # | Milestone | Description |
|---|-----------|-------------|
| 29 | Vector Database Evaluation | SQLite-vec or Chroma if JSONL performance degrades |
| 30 | Multi-user Support | Proper user isolation and authentication |
| 31 | Plugin System | Extensible tool and skill architecture |

---

## Development TODOs

### UI/UX Improvements
- [ ] **Add Shift+Enter to queue message** - Allow queuing messages while LLM is running
- [ ] **Normal Enter is steering mode** - Interject with it instead of waiting for completion
- [ ] **Add background color to tool call output** - Better visual distinction for tool calls
- [ ] **Keybind to toggle tool call output** - Show/hide tool call sections
- [ ] **Create PRD for ESC keybinding** - Add keyboard shortcut to cancel the current LLM call

### Reasoning & Agent Behavior
- [ ] **Remove max iterations limit** - Agent should run until completion or user cancellation
- [ ] **Investigate reasoning traces** - Save reasoning only for immediate previous turn, summarize/discard for older turns

### Edit Tool Safety
- [ ] **Ensure edit tool forces exact text matching**
  - Current issue: LLM sometimes guesses file state
  - Solution: Validate `oldText` matches current content exactly
  - Reject with clear error if mismatch detected
- [ ] **Add pre-edit validation**
  - Read file immediately before each edit
  - Compare against `oldText` parameter
  - Provide diff output when mismatch occurs

### Test Configuration
- [ ] **Skip integration and e2e tests during regular pytest runs**
  - Mark with `@pytest.mark.integration` / `@pytest.mark.e2e`
  - Configure `pyproject.toml` to exclude by default
- [ ] **Configure CI to run integration and e2e tests separately**
  - Keep unit tests fast for development feedback

### Code Quality
- [ ] **Fix pytest deprecation warnings**
  - `asyncio.iscoroutinefunction` → `inspect.iscoroutinefunction()`
  - Pydantic class-based `config` → `ConfigDict`
  - Register custom marks in `pyproject.toml`

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
KIMI_BASE_URL=https://api.kimi.com/coding/v1

# Optional
DEFAULT_LLM_PROVIDER=kimi
MEMORY_CONTEXT_LIMIT=20
EMBEDDING_MODEL=text-embedding-3-small
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-17 | JSONL over per-day files | Simpler, unified search, easier CRUD |
| 2026-02-17 | Single user, single agent | MVP simplicity |
| 2026-02-18 | Tool system with Pydantic | Automatic schema generation, validation |
| 2026-02-18 | Streaming agent loop | Real-time feedback, better UX |
| 2026-02-19 | Prompt-based learning | Learning is judgment-based; tools for deterministic ops |
| 2026-02-19 | Templates → data/ | Keeps templates clean, allows user reset |
| 2026-02-19 | Model-driven memory | Alfred decides what to remember, not automatic logging |
| 2026-02-19 | In-memory sessions | PRD #54; persistence planned for PRD #53 |
| 2026-02-20 | Rich Live for CLI markdown | Proper in-place markdown rendering without scrollback pollution |

---

## Notes

- Keep all memories forever (no automatic pruning)
- No encryption at rest (for now)
- Local development with Docker Compose
- Pre-commit hooks for code quality
- Stay with JSONL until search latency >100ms, then consider SQLite-vec
