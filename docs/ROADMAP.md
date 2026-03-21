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

Alfred uses a simplified memory architecture (PRD #102):

```
Files (Always Loaded, Durable):
├── SYSTEM.md              # Memory system architecture + cron capabilities
├── AGENTS.md              # Minimal behavior rules
├── USER.md                # User preferences
├── SOUL.md                # Alfred's personality
└── prompts/               # Modular prompt components
    ├── communication-style.md
    ├── voice.md
    └── memory-guidance.md

Memories (Curated, 90-day TTL):
└── memories.jsonl         # Semantic search, model decides writes

Session Archive (Automatic):
sessions/
└── {session_id}/
    ├── messages.jsonl     # Full conversation history
    └── summary.json       # Session summary for search
```

### Files (SYSTEM.md, AGENTS.md, USER.md, SOUL.md)

Always loaded in full every prompt. Expensive but always available.

| File | Purpose | Content |
|------|---------|---------|
| **SYSTEM.md** | Memory architecture + cron capabilities | Teaches Alfred how the system works |
| **AGENTS.md** | Minimal behavior rules | Permission First, Conventional Commits, Simple Correctness |
| **USER.md** | User preferences | Communication style, technical preferences |
| **SOUL.md** | Alfred's personality | Voice, boundaries, relationship with user |

**Model decides when to write.** Ask user first: "Should I add this to USER.md?"

#### Placeholder System

Any file can include content from other files using placeholders:

```markdown
# USER.md

{{prompts/communication-style.md}}

## Technical Preferences
{{prompts/tech-stack.md}}
```

**Syntax:** `{{relative/path/from/workspace.md}}`

**Resolution rules:**
- Path is relative to `~/.local/share/alfred/workspace/`
- Can reference `.md` files or any text file
- Nested placeholders allowed (A includes B, B includes C)
- Circular references detected and logged
- Missing files logged but don't crash
- Max depth: 5 levels

**Transparency:** Resolved placeholders are wrapped in HTML comments:
```markdown
<!-- included: prompts/communication-style.md -->
## Communication Style
- Prefers concise responses
<!-- end: prompts/communication-style.md -->
```

### Memories (Curated Store)

Model uses `remember` tool to save facts worth recalling.
- 90-day TTL (warns at 1000 memories by default)
- Semantic search via `search_memories`
- `permanent` flag to skip TTL
- No auto-capture, no auto-consolidation

**When to remember:** User says "remember this" or you decide a fact is worth keeping.

**When to search:** Before asking the user to repeat themselves.

### Session Archive

Full conversation history, searchable via `search_sessions`.
- Contextual retrieval: summaries → messages
- Use for: "what did we discuss last Tuesday?"

See PRD #102 for unified memory system details.

### Migration from Old Structure

**For existing users:** The three-tier memory model has been replaced. Your memories are preserved in `memories.jsonl`. Key changes:
- **TOOLS.md is phased out** — content moved to SYSTEM.md (cron) and USER.md (preferences)
- **AGENTS.md is simplified** — operational details removed, now references modular prompts
- **SYSTEM.md is new** — contains memory architecture guidance previously mixed into AGENTS.md

To migrate: Delete old AGENTS.md and TOOLS.md from your workspace. New templates will be created on next run.

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
| M13 | Code Health & Simplification - Removed 1,421 lines of dead code, duplication, over-engineering (PRD #82) |
| M14 | PyPiTUI CLI - Native scrollback, differential rendering, streaming responses, status line, input queue, command completion with fuzzy filtering (PRDs #94, #95, #97) |
| M15 | Config & Storage - XDG directories, TOML config, lock-free CAS JSONL store, context budget clarification (PRD #100) |
| M16 | Unified Memory System - Files + Memories (90-day TTL) + Session archive, placeholder system, TOOLS.md phase-out (PRD #102) |
| M17 | Session Summarization - Cron-based auto-summarization with two-stage search (PRD #76) |
| M18 | Tool Call Persistence - Persist tool calls in session, include in context, `/context` command (PRDs #101, #103) |
| M19 | Great Consolidation - Systematic cleanup: remove dead code, unify storage to SQLite, consolidate search logic (PRD #109) |
| M20 | Unified SQLite Storage - All storage (sessions, memories, cron) in single SQLite database with ACID transactions (PRD #117) |

### In Progress / Next Up 🔨

| # | Milestone | Description |
|---|-----------|-------------|
| 119 | ✅ AlfredCore + Standalone Cron | Extract shared services into AlfredCore class, enable standalone cron daemon for reliable background summarization (PRD #119) |
| 120 | ✅ Cron Job Linter + Socket API | AST-based linting to detect blocking calls, decouple Alfred from cron via socket API (PRD #120) |
| 88 | Programmatic Tool Calling | LLM writes Python code to orchestrate multiple tool calls in sandbox, reducing token consumption 30-50% |
| 90 | Multi-Provider LLM Support | z.ai, OpenRouter, Ollama with modal model selector |

### Short-term 📋

| # | Milestone | Description |
|---|-----------|-------------|
| 83 | ✅ Interactive Terminal Tool | E2E testing capability for AI agents to run CLIs interactively with visual capture (PRD #83) |
| 89 | Unified Notification System | Consistent notification formatting and prompt preservation (PRD #89) |
| 91 | Inline Streaming Renderer | Manual ANSI-based streaming markdown above prompt_toolkit prompt (PRD #91) |
| 105 | ✅ Local Embeddings + FAISS | BGE-base local embeddings and FAISS vector store for 5,400x faster search (PRD #105) |
| 14 | ✅ Cron Error Handling & UX | Friendly errors, local timezone, CLI responsiveness (PRD #75) |
| 15 | README Landing Page | Transform README into compelling OSS landing page |
| 21 | Testing & Quality | Comprehensive test coverage, fix deprecation warnings |
| 22 | Edit Tool Safety | Exact text matching validation, pre-edit verification |
| 23 | Test Configuration | Skip integration/e2e by default, separate CI jobs |
| 24 | Type Safety | Fix Tool class type safety, complete type annotations |
| 25 | ✅ Code Quality | Auto-fix Ruff violations, manual lint fixes (PRD #125) |
| 131 | Ctrl-T Tool Call Expansion | Toggle all tool call boxes to show full output (PRD #131) |
| 132 | Dynamic Embedding Dimension Support | Auto-detect and re-embed when switching models (BGE↔OpenAI) (PRD #132) |
| 135 | Persistent Memory Context | Keep memories loaded across turns with LRU eviction when limits reached (PRD #135) |
| 136 | ✅ Web-based UI | Alternative to TUI using FastAPI + WebSocket + Web Components for faster development velocity (PRD #136) |
| 140 | PyPiTUI v2 Adoption + Alfred Runtime Rewrite | Make PyPiTUI usable as a real runtime dependency and rewrite Alfred to consume it directly end-to-end (PRD #140) |

### Medium-term 📅

| # | Milestone | Description |
|---|-----------|-------------|
| 22 | Advanced Session Features | LLM context control, substring search, on-demand summaries |
| 24 | Configurable Context Budget | User-defined context percentages: 50% conversation, 10% tools, etc. |
| 25 | Local Embedding Models | Support for MiniLM, Nomic, MPNet running locally (no API calls) |
| 26 | HTTP API + Cron | Local API for scheduled actions |
| 139 | Web UI Test Fixture Realism | Replace bare MagicMock fixtures with explicit fakes and remove mock-aware Web UI shims (PRD #139) |

### Long-term 🔮

| # | Milestone | Description |
|---|-----------|-------------|
| 30 | Vector Database Evaluation | SQLite-vec or Chroma if JSONL performance degrades |
| 31 | Multi-user Support | Proper user isolation and authentication |
| 32 | Plugin System | Extensible tool and skill architecture |
| 33 | Advanced Tool Orchestration | Multi-step tool workflows with conditional logic and error recovery |

---

## Development TODOs

### UI/UX Improvements
- [ ] **Add Shift+Enter to queue message** - Allow queuing messages while LLM is running
- [ ] **Normal Enter is steering mode** - Interject with it instead of waiting for completion
- [ ] **Add background color to tool call output** - Better visual distinction for tool calls
- [x] **Keybind to toggle tool call output** - Ctrl-T expands all tool calls to show full output (PRD #131)
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
| 2026-02-19 | In-memory sessions | PRD #54 |
| 2026-02-20 | Rich Live for CLI markdown | Proper in-place markdown rendering without scrollback pollution |
| 2026-02-22 | Persistent sessions | PRD #53 - CLI commands, Telegram integration, context injection |
| 2026-02-25 | XDG directories | Standard Linux config paths (~/.config/alfred/) |
| 2026-02-26 | TOML config | Human-readable, better than JSON for configuration |
| 2026-02-26 | PyPiTUI for CLI | Native scrollback, differential rendering, single library |
| 2026-03-01 | CAS store | Lock-free concurrent writes with automatic retry |
| 2026-03-04 | Unified placeholder system | Single API for file includes {{path}} and colors {color}, extensible via Protocol pattern |
| 2026-03-04 | SYSTEM.md extraction | Contains memory architecture + cron capabilities (the "programming"), separates from AGENTS.md behavior rules |
| 2026-03-04 | AGENTS.md minimalism | Stripped to 3 core rules + communication guidelines, details extracted to prompts/agents/ |
| 2026-03-04 | TOOLS.md phase-out | Content moved to SYSTEM.md (cron capabilities) and USER.md (preferences), tool definitions from Pydantic schemas |
| 2026-03-04 | 90-day memory TTL | Extended from 30 days, warns at threshold instead of auto-pruning |
| 2026-03-04 | No backward compatibility | Direct update to ContextLoader, no legacy placeholder support needed |

---

## Notes

- Keep all memories forever (no automatic pruning)
- No encryption at rest (for now)
- Local development with Docker Compose
- Pre-commit hooks for code quality
- Stay with JSONL until search latency >100ms, then consider SQLite-vec
