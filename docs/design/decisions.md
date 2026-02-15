# Design Decisions

## Why One-Shot Pi Processes?

**Decision:** Spawn new Pi subprocess for each message (not persistent).

**Context:** Pi coding agent is designed for interactive TUI use. It doesn't support persistent background processes or stdin/stdout protocols.

**Options Considered:**
1. **Persistent processes** - Keep Pi running, communicate via stdin/stdout
   - *Rejected:* Pi doesn't support this; would require protocol changes
2. **One-shot mode** - Spawn per message with `--print` flag
   - *Chosen:* Native Pi behavior, session files maintain state
3. **Daemon mode** - Modify Pi to run as daemon
   - *Rejected:* Forking Pi is out of scope

**Consequences:**
- Simpler code (no process lifecycle management)
- Session files handle continuity
- Slightly higher latency (process spawn per message)
- No risk of zombie processes

## Why JSON for Thread Storage?

**Decision:** Store threads as JSON files, not database.

**Context:** Need persistent, human-readable thread state.

**Options Considered:**
1. **SQLite** - Relational database
   - *Rejected:* Overkill for simple key-value storage
2. **Redis** - In-memory with persistence
   - *Rejected:* External dependency, deployment complexity
3. **JSON files** - One file per thread
   - *Chosen:* Human-readable, git-friendly, no dependencies

**Consequences:**
- Easy to debug (just cat the file)
- Version controllable (if desired)
- No migration needed
- Works on any filesystem

## Why File-Based Memory?

**Decision:** Daily memory files (`memory/YYYY-MM-DD.md`) instead of database.

**Context:** AI agents need persistent memory across sessions.

**Options Considered:**
1. **Vector database** - Pinecone, Weaviate
   - *Rejected:* External dependency, cost, complexity
2. **SQLite with full-text search** - Local database
   - *Rejected:* Less inspectable than files
3. **Markdown files** - Daily notes + MEMORY.md
   - *Chosen:* Matches how humans journal, editable, portable

**Consequences:**
- User can edit memories directly
- Works with any text editor
- Easy to backup/sync
- Requires compaction strategy

## Why Separate handle_message and handle_command?

**Decision:** `Dispatcher.handle_message()` for regular messages, `handle_command()` for slash commands.

**Context:** Telegram supports bot commands (`/start`, `/status`).

**Options Considered:**
1. **Parse commands in handle_message** - Regex matching
   - *Rejected:* Fragile, hard to maintain
2. **Telegram CommandHandler** - Native Telegram support
   - *Chosen:* Proper command routing, help text, args parsing

**Consequences:**
- Clean separation of concerns
- Commands handled at bot level, not dispatcher
- Better user experience (command suggestions)

## Why Sub-agents?

**Decision:** Support `/subagent` command for background tasks.

**Context:** User wants long-running tasks without blocking main thread.

**Options Considered:**
1. **Async tasks** - Just run in background
   - *Chosen:* Simple, no external dependencies
2. **Celery/Redis** - Task queue
   - *Rejected:* Overkill for single-user bot
3. **Separate process pool** - Pre-spawned workers
   - *Rejected:* Resource intensive

**Consequences:**
- Background tasks don't block chat
- Results posted back to thread
- Limited by Python asyncio (one event loop)

## Why OpenAI Embeddings?

**Decision:** Support OpenAI embeddings with local fallback.

**Context:** Need semantic search over memories.

**Options Considered:**
1. **OpenAI only** - text-embedding-3-small
   - *Rejected:* Requires API key, network calls
2. **Local only** - sentence-transformers
   - *Rejected:* Heavy dependency (PyTorch)
3. **Hybrid** - OpenAI if key available, local fallback
   - *Chosen:* Flexible, works without API key (deterministic fallback)

**Consequences:**
- Best quality when API available
- Works offline with fallback
- Deterministic random embeddings for testing

## Why uv Instead of pip?

**Decision:** Use `uv` for Python package management.

**Context:** Need fast, reliable package installation.

**Options Considered:**
1. **pip** - Standard package manager
   - *Rejected:* Slow, dependency resolution issues
2. **poetry** - Modern Python packaging
   - *Rejected:* Complex lockfile format
3. **uv** - Rust-based, fast
   - *Chosen:* Fast, compatible with pip, simple

**Consequences:**
- Faster installs
- Better caching
- Still standard Python packaging

## Why hatchling Build Backend?

**Decision:** Use hatchling for package building.

**Context:** Need to build distributable Python package.

**Options Considered:**
1. **setuptools** - Standard
   - *Rejected:* Complex setup.py
2. **poetry** - Modern
   - *Rejected:* Non-standard metadata
3. **hatchling** - PEP 621 compliant
   - *Chosen:* Simple pyproject.toml, modern

**Consequences:**
- Standard pyproject.toml format
- Easy publishing to PyPI
- Good IDE support

## Why Parse Token Usage from Pi Sessions?

**Decision:** Parse actual token usage from Pi's JSONL session files instead of estimating.

**Context:** Need accurate token tracking for cost monitoring.

**Options Considered:**
1. **Character estimation** - 1 token ≈ 4 characters
   - *Rejected:* Wildly inaccurate for different languages/models
2. **Pi's session files** - Parse usage from JSONL entries
   - *Chosen:* Exact token counts, includes cache info, real cost data
3. **Provider API** - Query usage separately
   - *Rejected:* No unified API, extra network calls

**Consequences:**
- Accurate token counts per request
- Cache hit/miss tracking
- Real cost data from provider
- Requires parsing JSONL files

## Why Verbose Logging to Telegram?

**Decision:** Add `/verbose` command to send DEBUG logs to Telegram chat.

**Context:** Hard to debug production issues without log access.

**Options Considered:**
1. **File logs only** - Write to disk, user ssh's in
   - *Rejected:* User doesn't have server access
2. **Webhook logging** - External logging service
   - *Rejected:* External dependency, privacy concerns
3. **Telegram messages** - Send logs as chat messages
   - *Chosen:* Immediate, no extra setup, user already in chat

**Consequences:**
- Real-time debugging in chat
- Can get spammy with DEBUG level
- Must truncate long messages (>4000 chars)
- Per-chat enable/disable

## Why LLM-Based Memory Compaction?

**Decision:** Use LLM to compact daily memories into MEMORY.md summary.

**Context:** Raw daily notes are too verbose for long-term storage.

**Options Considered:**
1. **Rule-based extraction** - Parse headers and bullet points
   - *Rejected:* Misses context, can't synthesize across days
2. **LLM summarization** - Send memories to LLM, get summary
   - *Chosen:* Intelligent synthesis, natural language output
3. **No compaction** - Keep all daily files forever
   - *Rejected:* Too many files, hard to find important info

**Consequences:**
- Intelligent summaries that capture what's important
- Configurable via custom prompts
- Costs API tokens to run
- Archives original files after compaction

## Why Simplified `/compact` Interface?

**Decision:** `/compact [optional prompt]` instead of strategy/days parameters.

**Context:** Original design had `/compact <strategy> <days>` - too complex.

**Options Considered:**
1. **Multi-parameter** - Strategy, days, provider, model
   - *Rejected:* Too many options, confusing UX
2. **Prompt-based** - Just optional custom prompt
   - *Chosen:* Natural language, flexible, simple
3. **Interactive** - Bot asks questions
   - *Rejected:* Slow, interrupts workflow

**Consequences:**
- Simple: `/compact` just works
- Powerful: Custom prompt controls behavior
- Compacts ALL memories (not just recent days)
- No need to remember strategy names

## Why Shared Workspace?

**Decision:** Add shared workspace accessible across all threads.

**Context:** Threads are isolated - need way to share data between them.

**Options Considered:**
1. **Thread merging** - Allow threads to access each other's data
   - *Rejected:* Breaks isolation model
2. **Database** - Shared SQL database
   - *Rejected:* External dependency
3. **File-based shared workspace** - `shared/notes/`, `shared/data/`
   - *Chosen:* Simple, works with existing file tools

**Consequences:**
- Cross-thread collaboration possible
- Notes and data files persist across conversations
- User can organize shared content
- Requires careful naming to avoid conflicts
