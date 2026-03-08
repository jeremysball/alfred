# Memory & Session System Report

## Executive Summary

Alfred's memory and session systems provide persistent, searchable conversation history with semantic retrieval capabilities. The system uses SQLite for unified storage, vector embeddings for similarity search, and a cron-based session summarizer for efficient retrieval.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MEMORY SYSTEM                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  Files (Always Loaded)                                                   │
│  ├── SYSTEM.md          # Memory architecture + cron capabilities        │
│  ├── AGENTS.md          # Behavior rules                                 │
│  ├── USER.md            # User preferences                               │
│  └── SOUL.md            # Alfred's personality                           │
│                                                                          │
│  Curated Memories (90-day TTL)                                           │
│  └── memories.jsonl     # Semantic search, model decides writes          │
│       └── OpenAI embeddings (1536-dim)                                   │
│                                                                          │
│  Session Archive (Automatic)                                             │
│  └── sessions/          # Full conversation history                      │
│       ├── {session_id}/                                                  │
│       │   ├── messages.jsonl    # Messages with embeddings               │
│       │   └── summary.json      # LLM summary for search                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technologies Used

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Storage Backend** | SQLite + aiosqlite | Unified ACID-compliant storage |
| **Vector Search** | sqlite-vec | Efficient vector similarity search |
| **Embeddings** | OpenAI text-embedding-3-small (1536-dim) | Semantic vector generation |
| **Alternative** | BGE-base local (768-dim) | Free, faster local option |
| **Persistence** | JSON + SQLite WAL mode | Concurrent access, crash safety |

---

## Key Classes & Components

### Memory System

| File | Class | Purpose |
|------|-------|---------|
| `src/alfred/memory/base.py` | `MemoryEntry` | Dataclass for memory content + metadata |
| `src/alfred/memory/sqlite_store.py` | `SQLiteMemoryStore` | Production memory store implementation |
| `src/alfred/storage/sqlite.py` | `SQLiteStore` | Unified storage (sessions + memories + cron) |
| `src/alfred/tools/remember.py` | `RememberTool` | Tool for saving memories |
| `src/alfred/tools/search_memories.py` | `SearchMemoriesTool` | Semantic memory search |
| `src/alfred/tools/forget.py` | `ForgetTool` | Memory deletion |

### Session System

| File | Class | Purpose |
|------|-------|---------|
| `src/alfred/session.py` | `SessionManager` | Manages chat sessions (factory-injected) |
| `src/alfred/session.py` | `Session` | In-memory session with messages |
| `src/alfred/session.py` | `Message` | Individual chat message |
| `src/alfred/tools/search_sessions.py` | `SearchSessionsTool` | Two-stage session retrieval |
| `src/alfred/tools/search_sessions.py` | `SessionSummarizer` | LLM-based session summarization |

### Factories (Dependency Injection)

| Factory | Creates |
|---------|---------|
| `SQLiteStoreFactory` | `SQLiteStore` |
| `EmbeddingProviderFactory` | `EmbeddingProvider` |
| `LLMProviderFactory` | `LLMProvider` |
| `MemoryStoreFactory` | `MemoryStore` |
| `SessionManagerFactory` | `SessionManager` |
| `SessionSummarizerFactory` | `SessionSummarizer` |

---

## Session Summarizer Job

### Configuration

**Location:** `src/alfred/cron/system_jobs.py`

```python
"session_summarizer": (
    "*/5 * * * *",  # Runs every 5 minutes
    '''"""Summarize idle sessions with 30min idle or 20+ new messages."""
    
    IDLE_THRESHOLD_MINUTES = 30
    MESSAGE_THRESHOLD = 20
''',
)
```

### Trigger Conditions

The summarizer runs every 5 minutes and processes sessions that meet EITHER condition:

1. **Idle time**: Session idle for > 30 minutes
2. **Message count**: 20+ new messages since last summary

### Logging Behavior

**YES, the session summarizer job logs when it runs.**

The job uses `print()` statements that are captured by the cron executor:

```python
async def run():
    """Find and summarize eligible sessions."""
    print("Running session summarization job")  # ← START log
    
    # ... processing ...
    
    if should_summarize:
        print(f"Summarizing session {meta.session_id}")  # ← PER-SESSION log
        # ... generate summary ...
        print(f"Saved summary for session {meta.session_id}")  # ← SUCCESS log
    
    print(f"Session summarization complete: {summarized} sessions summarized")  # ← END log
```

### Log Capture & Storage

The `JobExecutor` captures all stdout/stderr and stores it in execution history:

```python
# From src/alfred/cron/executor.py
with (
    redirect_stdout(stdout_capture),
    redirect_stderr(stderr_capture),
):
    await self._execute_with_timeout()

# Results stored in ExecutionResult
return ExecutionResult(
    status=ExecutionStatus.SUCCESS,
    stdout=stdout,  # ← Contains all print() output
    stderr=stderr,
    ...
)
```

### Viewing Logs

**Via CLI:**
```bash
# List recent executions
uv run alfred cron history session_summarizer

# View detailed output
uv run alfred cron logs session_summarizer --last
```

**Storage Location:**
- Execution records: `~/.local/share/alfred/cron_history.jsonl`
- Contains: `stdout`, `stderr`, `duration_ms`, `memory_peak_mb`, `status`

### Sample Log Output

```
Running session summarization job
Summarizing session abc123...
Saved summary for session abc123
Summarizing session def456...
Saved summary for session def456
Session summarization complete: 2 sessions summarized
```

---

## Database Schema

### Tables

```sql
-- Sessions table
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    messages JSON NOT NULL DEFAULT '[]',
    message_count INTEGER DEFAULT 0
);

-- Session summaries for semantic search
CREATE TABLE session_summaries (
    summary_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    embedding JSON,
    message_count INTEGER NOT NULL,
    first_message_idx INTEGER NOT NULL,
    last_message_idx INTEGER NOT NULL,
    version INTEGER DEFAULT 1,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Message embeddings for vector search
CREATE TABLE message_embeddings (
    message_embedding_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_idx INTEGER NOT NULL,
    role TEXT NOT NULL,
    content_snippet TEXT,
    embedding JSON NOT NULL
);

-- Memories (curated facts)
CREATE TABLE memories (
    entry_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tags JSON DEFAULT '[]',
    permanent BOOLEAN DEFAULT 0
);

-- Virtual table for vector search (sqlite-vec)
CREATE VIRTUAL TABLE memory_embeddings USING vec0(
    entry_id TEXT PRIMARY KEY,
    embedding FLOAT[768]
);
```

---

## Two-Stage Session Search (PRD #76)

### Stage 1: Summary Search

1. Embed the search query
2. Search `session_summaries` table via sqlite-vec
3. Return top-k matching sessions

### Stage 2: Message Search

1. For each matching session
2. Search `message_embeddings` within that session
3. Return specific relevant messages

### Code Flow

```python
# From SearchSessionsTool
async def execute_stream(self, **kwargs):
    # Stage 1: Find relevant sessions
    relevant_summaries = await self.summarizer.store.search_summaries(
        query_embedding, top_k
    )
    
    # Stage 2: Search messages within each session
    for summary in relevant_summaries:
        messages = await self.summarizer.store.search_session_messages(
            session_id, query_embedding, top_k
        )
```

---

## Memory Lifecycle

### Creating a Memory

```python
from alfred.memory import MemoryEntry
from datetime import datetime

entry = MemoryEntry(
    entry_id="unique-id",
    timestamp=datetime.now(),
    role="system",
    content="User prefers dark mode",
    tags=["preferences", "ui"],
    permanent=True,  # Skip 90-day TTL
)
await memory_store.add(entry)
```

### TTL (Time To Live)

- **Default:** 90 days for non-permanent memories
- **Permanent:** Never expires (set `permanent=True`)
- **Pruning:** Manual or cron job removes expired memories

### Semantic Search

```python
results, similarities, scores = await memory_store.search(
    query="user interface preferences",
    top_k=5
)
```

---

## Testing

### Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/test_session.py` | 18 | Session CRUD, persistence |
| `tests/test_session_context.py` | 7 | Context building |
| `tests/test_tools_edit.py` | 24 | Edit tool functionality |
| `tests/test_token_tracker.py` | 5 | Token tracking |

### Run Tests

```bash
uv run pytest tests/test_session.py tests/test_session_context.py -v
```

---

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=xxx           # For embeddings
KIMI_API_KEY=xxx             # For LLM

# Optional
EMBEDDING_PROVIDER=openai    # or 'local' for BGE
MEMORY_CONTEXT_LIMIT=20      # Max memories in context
```

### Data Directory

Default: `~/.local/share/alfred/`

Structure:
```
~/.local/share/alfred/
├── alfred.db              # SQLite database
├── sessions/
│   └── current.json       # Current CLI session ID
├── cron.jsonl             # Cron jobs
└── cron_history.jsonl     # Execution history
```

---

## Summary

| Feature | Status |
|---------|--------|
| Session storage | ✅ SQLite with JSON messages |
| Session search | ✅ Two-stage (summary → messages) |
| Session summarizer job | ✅ Runs every 5 minutes |
| **Job logging** | **✅ YES - Captured stdout/stderr** |
| Memory storage | ✅ SQLite with vector embeddings |
| Memory TTL | ✅ 90 days (configurable) |
| Semantic search | ✅ Cosine similarity via sqlite-vec |
| Dependency injection | ✅ Factory pattern |
| Test coverage | ✅ 49 tests passing |
