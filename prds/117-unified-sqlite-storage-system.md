# PRD: Unified SQLite Storage System

## Overview

**Issue**: #117
**Parent**: #109 (Great Consolidation)
**Status**: In Progress
**Priority**: High
**Created**: 2026-03-07

Consolidate all storage (sessions, memories, cron jobs) into a single SQLite database with ACID transactions, unified interface, and vector search via sqlite-vec.

---

## Problem Statement

Current storage is fragmented across multiple JSONL files:

| Data Type | Current Storage | Problems |
|-----------|-----------------|----------|
| Sessions | `data/sessions/{id}/messages.jsonl` | Directory per session, file I/O overhead |
| Memories | `data/memory/memories.jsonl` | Concurrent write conflicts, no ACID |
| Cron Jobs | `data/cron.jsonl` | Separate file, inconsistent patterns |
| Session Summaries | Not yet implemented | Needs storage layer |

**Issues with file-based storage:**
- No ACID guarantees — crashes can corrupt data
- File locking problems under concurrent access
- Complex backup (multiple files)
- Inconsistent query patterns
- Slow at scale (O(n) file reads)

---

## Solution

Single SQLite database (`data/alfred.db`) with unified `SQLiteStore` class.

### Architecture

```
data/
├── alfred.db                    # Single SQLite database
│   ├── sessions                 # Session metadata + messages JSON
│   ├── session_summaries        # LLM-generated summaries with embeddings
│   ├── memories                 # Curated facts with embeddings
│   ├── memory_embeddings        # sqlite-vec virtual table
│   ├── cron_jobs                # Scheduled jobs
│   └── cron_history             # Job execution history
└── sessions/
    └── current.json             # CLI current session pointer (legacy)
```

### SQLiteStore Interface

```python
class SQLiteStore:
    """Unified SQLite storage for all Alfred data."""
    
    # Sessions
    async def save_session(session_id: str, messages: list[dict]) -> None
    async def load_session(session_id: str) -> dict | None
    async def list_sessions(limit: int = 100) -> list[dict]
    
    # Session Summaries
    async def save_summary(summary: SessionSummary) -> None
    async def get_latest_summary(session_id: str) -> SessionSummary | None
    async def find_sessions_needing_summary(threshold: int) -> list[str]
    
    # Memories
    async def add_memory(entry: MemoryEntry) -> None
    async def search_memories(query_embedding: list[float], top_k: int) -> list[dict]
    async def get_memory(entry_id: str) -> dict | None
    
    # Cron
    async def save_job(job: CronJob) -> None
    async def list_pending_jobs() -> list[CronJob]
    async def record_execution(record: ExecutionRecord) -> None
```

---

## Database Schema

### Sessions Table

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    messages JSON NOT NULL DEFAULT '[]',
    message_count INTEGER DEFAULT 0
);

CREATE INDEX idx_sessions_updated ON sessions(updated_at);
```

**Messages JSON structure:**
```json
[
  {
    "idx": 0,
    "role": "user",
    "content": "...",
    "timestamp": "2026-03-07T10:00:00Z",
    "embedding": [0.1, 0.2, ...],
    "input_tokens": 10,
    "output_tokens": 50
  }
]
```

### Session Summaries Table

```sql
CREATE TABLE session_summaries (
    summary_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER NOT NULL,
    first_message_idx INTEGER NOT NULL,
    last_message_idx INTEGER NOT NULL,
    summary_text TEXT NOT NULL,
    embedding JSON,              -- Stored as JSON array
    version INTEGER DEFAULT 1,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX idx_session_summaries_session ON session_summaries(session_id);
CREATE INDEX idx_session_summaries_created ON session_summaries(created_at);
```

### Memories Table

```sql
CREATE TABLE memories (
    entry_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tags JSON DEFAULT '[]',
    permanent BOOLEAN DEFAULT 0
);

CREATE INDEX idx_memories_timestamp ON memories(timestamp);
CREATE INDEX idx_memories_permanent ON memories(permanent);
```

### Memory Embeddings (sqlite-vec)

```sql
-- Virtual table for vector search (requires sqlite-vec extension)
CREATE VIRTUAL TABLE IF NOT EXISTS memory_embeddings USING vec0(
    entry_id TEXT PRIMARY KEY,
    embedding FLOAT[768]  -- Configurable dimension
);
```

**Fallback without sqlite-vec:** Store embedding as JSON in `memories.embedding` column, use brute-force search.

### Cron Jobs Table

```sql
CREATE TABLE cron_jobs (
    job_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    schedule TEXT NOT NULL,
    command TEXT NOT NULL,
    enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    metadata JSON DEFAULT '{}'
);

CREATE INDEX idx_cron_jobs_next_run ON cron_jobs(next_run_at) WHERE enabled = 1;
```

### Cron History Table

```sql
CREATE TABLE cron_history (
    execution_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,
    output TEXT,
    error TEXT,
    FOREIGN KEY (job_id) REFERENCES cron_jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX idx_cron_history_job ON cron_history(job_id, started_at DESC);
```

---

## Migration Strategy

### Phase 1: Create SQLiteStore (COMPLETE)
- Implement `SQLiteStore` class
- Add schema creation methods
- Write tests

### Phase 2: Migrate Sessions (COMPLETE)
- `SessionManager` now uses `SQLiteStore`
- `sessions` table created
- Old `SessionStorage` removed

### Phase 3: Migrate Memories (COMPLETE)
- `SQLiteMemoryStore` implements `MemoryStore` interface
- `memories` table created
- Old `JSONLMemoryStore` and `FAISSMemoryStore` removed

### Phase 4: Migrate Cron (COMPLETE)
- Cron jobs stored in SQLite
- Old `CronStore` (JSONL) removed

### Phase 5: Add Session Summaries (IN PROGRESS)
- Create `session_summaries` table
- Implement summary storage methods
- Integrate with `SessionSummarizer`

---

## Configuration

```toml
[storage]
database_path = "data/alfred.db"
wal_mode = true              # Write-ahead logging for better concurrency

[storage.vector_search]
provider = "sqlite-vec"      # "sqlite-vec" or "brute-force"
embedding_dimension = 768
```

---

## Performance Considerations

| Metric | JSONL | SQLite | Notes |
|--------|-------|--------|-------|
| Concurrent writes | Poor (file locks) | Good (WAL mode) | WAL = Write-Ahead Logging |
| Query with index | O(n) | O(log n) | Indexed lookups |
| Startup time | Slow (load all files) | Fast (lazy) | SQLite is already initialized |
| Backup | Complex (many files) | Simple (single file) | Just copy `alfred.db` |
| ACID compliance | No | Yes | Transactions guarantee consistency |

---

## Error Handling

**Database corruption:**
- SQLite has built-in corruption detection
- Backup strategy: periodic `.backup` command
- Recovery: restore from backup, replay from session history

**sqlite-vec not available:**
- Detect at startup
- Fall back to JSON embedding storage
- Use brute-force cosine similarity
- Log warning

**Concurrent access:**
- WAL mode handles readers + single writer
- Timeout on busy: retry with exponential backoff
- Raise `StorageBusyError` after max retries

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-07 | SQLite over JSONL | ACID transactions, better concurrency, single file backup |
| 2026-03-07 | Separate tables per entity | Proper relational model, foreign keys, type safety |
| 2026-03-07 | sqlite-vec for vectors | Native vector search in SQLite, fallback to brute-force |
| 2026-03-07 | WAL mode enabled | Better read concurrency, faster writes |
| 2026-03-07 | JSON for embeddings fallback | Portable, no extension required, acceptable for small scale |

---

## Dependencies

- ✅ `aiosqlite` — Async SQLite driver
- ✅ `sqlite-vec` — Vector search extension (optional)
- Replaces: `JSONLMemoryStore`, `FAISSMemoryStore`, `SessionStorage`, `CronStore`

---

## Future: Distributed Storage

If multi-instance support needed:
- PostgreSQL + pgvector
- Cloud SQLite (Litestream for replication)
- Keep SQLite for single-user, add abstraction layer

---

## Acceptance Criteria

- [ ] All data stored in single SQLite file
- [ ] ACID transactions for all writes
- [ ] sqlite-vec working for memory search
- [ ] Fallback to brute-force if sqlite-vec unavailable
- [ ] Old JSONL stores removed
- [ ] Migration path tested
- [ ] Backup/restore documented
