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
