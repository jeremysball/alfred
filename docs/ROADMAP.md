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
│   ├── session_summaries.jsonl  # Session summaries with embeddings
│   └── context/                 # Working copies of templates
└── tests/
```

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

### In Progress / Next Up 🔨

| # | Milestone | Description |
|---|-----------|-------------|
| 12 | Session Summarization | Cron-based auto-summarization (30 min idle or 20 messages) |
| 13 | Learning System | Prompt-based learning to update USER.md/SOUL.md |
| 14 | Cron Error Handling & UX | Friendly errors, local timezone, CLI responsiveness |
| 15 | Rich Markdown Output | Streaming markdown-to-ANSI rendering for CLI |
| 16 | README Landing Page | Transform README into compelling OSS landing page |

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
| 23 | HTTP API + Cron | Local API for scheduled actions |
| 24 | Config TOML Migration | Replace config.json with alfred.toml |
| 25 | Observability & Logging | Structured logging, tracing, metrics |

### Long-term 🔮

| # | Milestone | Description |
|---|-----------|-------------|
| 26 | Vector Database Evaluation | SQLite-vec or Chroma if JSONL performance degrades |
| 27 | Multi-user Support | Proper user isolation and authentication |
| 28 | Plugin System | Extensible tool and skill architecture |

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
KIMI_BASE_URL=https://api.moonshot.cn/v1

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
| 2026-02-19 | Dual embeddings | Messages for facts, sessions for context |
| 2026-02-19 | Cron-based summarization | Decoupled, handles idle detection cleanly |

---

## Notes

- Keep all memories forever (no automatic pruning)
- No encryption at rest (for now)
- Local development with Docker Compose
- Pre-commit hooks for code quality
- Stay with JSONL until search latency >100ms, then consider SQLite-vec
