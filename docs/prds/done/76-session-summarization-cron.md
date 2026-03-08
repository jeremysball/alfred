# PRD: Session Summarization with Cron

## Overview

**Issue**: #76
**Parent**: #10 (Alfred - The Rememberer)
**Depends On**: #53 (Session System), #21 (M11: Learning System)
**Status**: In Progress
**Priority**: High
**Created**: 2026-02-19

## Implementation Progress

### ✅ Completed
- **Phase 1: SQLite Storage Layer**
  - [x] `session_summaries` table with FK constraint to `sessions`
  - [x] Indexes on `session_id` and `created_at`
  - [x] `save_summary()` method with embedding serialization
  - [x] `get_latest_summary()` method (returns most recent by version)
  - [x] `find_sessions_needing_summary()` method (threshold-based query)
  - [x] `message_count` column added to `sessions` table

### ⏳ Remaining
- **Phase 2: SessionSummarizer Integration**
  - [ ] Update `SessionSummarizer` to use SQLite instead of JSON files
  - [ ] LLM integration for `generate_summary()`
  
- **Phase 3: Cron Job Wiring**
  - [ ] Update `session_summarizer` system job to actually generate summaries
  - [ ] Wire up `SessionSummarizer` in job context
  
- **Phase 4: Two-Stage Search**
  - [ ] Implement `_find_relevant_sessions()` for semantic search
  - [ ] Implement `_search_session_messages()` for in-session search
  - [ ] Update `SearchSessionsTool.execute_stream()` for two-stage flow
  
- **Phase 5: Integration & Testing**
  - [ ] Pass `llm_client` to `register_builtin_tools()`
  - [ ] End-to-end integration test

**Overall Progress: 25%** (2 of 5 phases complete)

Implement automatic session summarization using cron jobs. Sessions are summarized after 30 minutes of inactivity or 20 messages, enabling dual embedding search (messages + summaries).

---

## Problem Statement

Current memory search finds individual messages but loses session context. Users ask "What did we discuss about my project?" and get scattered facts without the narrative thread. Session summaries preserve the arc of conversations — the decisions, pivots, and conclusions that individual messages miss.

---

## Solution

Create automatic session summarization:
1. Tag every message with `session_id`
2. Cron job runs every few minutes, checking for:
   - Sessions idle >30 minutes (ready to summarize)
   - Sessions with 20+ new messages since last summary
3. Generate summary via LLM, embed it, store in `session_summaries.jsonl`
4. Replace previous summary (not append) for same session
5. Dual search: messages for specifics, summaries for context

---

## Acceptance Criteria

- [x] `session_id` field on all memory entries — ✅ `SessionMeta` has `session_id`
- [x] SQLite `session_summaries` storage with embeddings — ✅ Table created with FK constraint
- [ ] Cron job for automatic summarization (30 min idle OR 20 msg threshold) — ⏳ Job defined but doesn't call LLM
- [ ] `search_sessions` tool for semantic session search — ⏳ Basic version exists, needs two-stage search
- [x] Session summaries replaceable (regenerate, don't append) — ✅ Schema supports versioning
- [x] Session metadata tracks: message count, timestamp range, summary version — ✅ `message_count` column added, `version` in summaries

---

## Storage Architecture

Uses **SQLite** (not JSON files) for unified storage via `SQLiteStore`:

```
data/
├── alfred.db                    # SQLite database with all tables
│   ├── sessions                 # Session metadata + messages JSON
│   ├── session_summaries        # LLM-generated summaries with embeddings
│   ├── memories                 # Curated facts with embeddings
│   └── cron_jobs/history        # Scheduled jobs
└── sessions/
    └── current.json             # CLI current session pointer only
```

**Note:** PRD originally specified per-session `summary.json` files. Implementation uses dedicated `session_summaries` table with proper foreign key relationships.

---

## Session Identification

Messages get `session_id` assigned on write:

```python
@dataclass
class MemoryEntry:
    id: str
    timestamp: datetime
    role: str  # "user" | "assistant"
    content: str
    embedding: list[float]
    session_id: str  # NEW: Groups messages into sessions
    importance: float = 0.5
```

**Session boundary detection:**
- New session starts when:
  - No session exists yet
  - Previous message was >30 minutes ago
  - User explicitly starts new session (optional future)

```python
def assign_session_id(
    new_message_time: datetime,
    last_message_time: datetime | None,
    current_session_id: str | None,
) -> str:
    """Assign session ID based on time gap."""
    SESSION_GAP_MINUTES = 30
    
    if current_session_id is None:
        return generate_session_id()
    
    gap = (new_message_time - last_message_time).total_seconds() / 60
    if gap > SESSION_GAP_MINUTES:
        return generate_session_id()  # New session
    
    return current_session_id  # Continue current session
```

---

## Session Summary Storage

Dedicated `session_summaries` table with foreign key to sessions.

```python
@dataclass
class SessionSummary:
    summary_id: str            # Unique summary ID (UUID)
    session_id: str            # Foreign key to sessions.session_id
    created_at: datetime       # When summary created
    message_count: int         # Messages summarized
    first_message_idx: int     # First message index in session
    last_message_idx: int      # Last message index in session
    summary_text: str          # LLM-generated summary
    embedding: list[float]     # For semantic search
    version: int               # Increment on regeneration
```

**SQLite schema:**
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

CREATE INDEX idx_session_summaries_session 
ON session_summaries(session_id);

CREATE INDEX idx_session_summaries_created 
ON session_summaries(created_at);
```

**Query patterns:**
```sql
-- Get latest summary for session
SELECT * FROM session_summaries 
WHERE session_id = ? 
ORDER BY version DESC 
LIMIT 1;

-- Find summaries needing regeneration
SELECT s.session_id, s.message_count, sm.version, sm.last_message_idx
FROM sessions s
LEFT JOIN session_summaries sm ON s.session_id = sm.session_id
WHERE s.message_count - COALESCE(sm.message_count, 0) >= 20;
```

---

## Cron Job Implementation

**Schedule:** Every 5 minutes (configurable)

**Logic:**
```python
async def summarize_sessions_job(config: Config) -> None:
    """Cron job: Find sessions needing summary and generate them."""
    
    IDLE_THRESHOLD_MINUTES = 30
    MESSAGE_THRESHOLD = 20
    
    # Get all active sessions with message counts
    sessions = await get_active_sessions()
    
    for session in sessions:
        messages_since_summary = session.total_messages - session.last_summarized_count
        minutes_idle = (now() - session.last_message_time).total_seconds() / 60
        
        should_summarize = (
            minutes_idle > IDLE_THRESHOLD_MINUTES or
            messages_since_summary >= MESSAGE_THRESHOLD
        )
        
        if should_summarize:
            await generate_session_summary(session)


async def generate_session_summary(session: Session) -> SessionSummary:
    """Generate and store session summary."""
    
    # Get all messages in session
    messages = await get_session_messages(session.id)
    
    # Check for existing summary (query SQLite)
    existing = await get_latest_session_summary(session.id)
    
    # Generate summary via LLM
    summary_text = await llm.summarize_conversation(messages)
    
    # Create embedding
    embedding = await embedder.create_embedding(summary_text)
    
    # Build summary with new version
    summary = SessionSummary(
        summary_id=generate_id(),
        session_id=session.id,
        created_at=now(),
        message_count=len(messages),
        first_message_idx=0,
        last_message_idx=len(messages) - 1,
        summary_text=summary_text,
        embedding=embedding,
        version=(existing.version + 1) if existing else 1,
    )
    
    # Insert into session_summaries table
    await store_summary(summary)
    
    return summary
```

**Key behaviors:**
- **Replace, don't append:** New summaries overwrite conceptually (write new line with updated version)
- **Full regeneration:** Always summarize from session start, not just new messages
- **Idempotent:** Running twice produces same result (same messages → same summary)

---

## Search Tools

Two separate tools, no merging:

### 1. search_memories (existing)
Searches curated facts that Alfred has explicitly remembered.

```python
class SearchMemoriesTool:
    """Search curated memory entries."""
    
    async def execute(self, query: str, top_k: int = 5) -> ToolResult:
        query_embedding = await embedder.create_embedding(query)
        
        # Search memories.jsonl (curated facts only)
        results = await search_by_similarity(
            query_embedding=query_embedding,
            index_path="data/memory/memories.jsonl",
            top_k=top_k,
        )
        
        return ToolResult(content=format_results(results))
```

### 2. search_sessions (new)
Searches session summaries for broader context.

```python
class SearchSessionsTool:
    """Search session summaries for conversation context."""
    
    name = "search_sessions"
    description = """Search summaries of past conversations.
    
    Use when the user asks about:
    - "What did we discuss about X?"
    - "When did we talk about Y?"
    - Topics spanning multiple exchanges
    - The overall arc of a conversation
    """
    
    async def execute(self, query: str, top_k: int = 3) -> ToolResult:
        query_embedding = await embedder.create_embedding(query)
        
        # Search all summary.json files in sessions folder
        results = await search_session_summaries(
            query_embedding=query_embedding,
            sessions_dir="data/sessions",
            top_k=top_k,
        )
        
        return ToolResult(content=format_session_results(results))
```

**When to use which:**
- **search_memories:** Specific facts Alfred has curated (via `remember` tool)
- **search_sessions:** Themes, projects, decisions, conversation arcs

---

## Interaction Examples

**Specific fact:**
```
User: What database did we decide on?
Alfred: [search_memories: "database decision"]
→ Found: "Let's use PostgreSQL with asyncpg" (message 34)
```

**Broad context:**
```
User: What did we discuss about my project?
Alfred: [search_sessions: "user project discussion"]
→ Found session summary: "Discussed database architecture (PostgreSQL vs SQLite), 
    decided on PostgreSQL. Then moved to API design..."
```

**Both:**
```
User: Remind me about the authentication work
Alfred: [search_sessions: "authentication"]
→ Found session: "3 days ago, discussed auth patterns for 45 minutes"

Alfred: [search_memories: "jwt secret key config"]
→ Found: "Store JWT_SECRET in .env, not code" (message 12)
```

---

## Configuration

```toml
[session]
summarize_idle_minutes = 30      # Trigger after idle time
summarize_message_threshold = 20 # Trigger after N new messages
cron_interval_minutes = 5        # How often to check

[storage]
database_path = "data/alfred.db" # SQLite database path
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-19 | Cron job, not event-driven | Simpler, decoupled, handles idle detection cleanly |
| 2026-02-19 | 30 min idle / 20 msg threshold | Balance freshness vs. stability |
| 2026-02-19 | Replace summaries (versioned) | Avoid accumulation, always have current view |
| 2026-02-19 | Separate search tools | Clear UX: specific vs. broad intent |
| 2026-02-19 | session_id on messages | Clean linkage, enables session queries |
| 2026-03-07 | SQLite with dedicated `session_summaries` table | Unified storage architecture (PRD #109); proper relational schema with foreign keys; easier querying and indexing than JSON metadata |

---

## Dependencies

- ✅ #53 (Session System) — Message storage, session tracking
- ✅ #21 (M11: Learning System) — Context for summary generation
- Existing embedding client
- Existing cron infrastructure

---

## Future: Triple-Layer Memory Architecture

This PRD implements dual search (curated memories + session summaries). PRD #77 adds **per-session message embeddings** for contextual retrieval:

1. **Curated Memory** (SQLite `memories` table) — Facts Alfred explicitly remembers
2. **Session Summaries** (SQLite `session_summaries` table) — Narrative arcs with embeddings ← THIS PRD
3. **Session Messages** (SQLite `sessions.messages` JSON column) — Individual messages with embeddings

**The Hyperweb Retrieval Pattern:**
```
Query → Find relevant sessions (via summary similarity)
            ↓
    Search messages ONLY within those sessions
            ↓
    Higher precision, natural context expansion
```

Instead of searching all messages globally, narrow to 2-3 relevant sessions, then find specifics. See PRD #77 (Contextual Retrieval System) for implementation.

## Vector Database Discussion

**Current approach (SQLite + sqlite-vec):**
- Pros: Single database file, ACID transactions, fast indexed queries, sqlite-vec for vector similarity
- Cons: sqlite-vec is an extension (requires loadable extension support)

**Fallback (SQLite without sqlite-vec):**
- Embeddings stored as JSON in `embedding` column
- Brute-force cosine similarity in Python for small datasets (<10K entries)
- Acceptable for single-user local deployment

**When to consider a dedicated vector DB:**
- >100K memories (brute-force search becomes slow)
- Need complex metadata filtering across multiple tables
- Multiple Alfred instances (shared state)
- Need hybrid search (vector + full-text + metadata)

**Recommended if you switch:**
- **Chroma** — Embedded, zero-config, good for single-user local
- **pgvector** — If already using PostgreSQL

**Not recommended:**
- Pinecone/Weaviate for local single-user (overkill)

**Verdict:** SQLite + sqlite-vec is sufficient for current scale. Revisit if search latency >100ms for typical queries.
