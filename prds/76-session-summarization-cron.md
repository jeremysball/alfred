# PRD: Session Summarization with Cron

## Overview

**Issue**: #76
**Parent**: #10 (Alfred - The Rememberer)
**Depends On**: #53 (Session System), #21 (M11: Learning System)
**Status**: Planning
**Priority**: High
**Created**: 2026-02-19

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

- [ ] `session_id` field on all memory entries
- [ ] `data/session_summaries.jsonl` storage with embeddings
- [ ] Cron job for automatic summarization (30 min idle OR 20 msg threshold)
- [ ] `search_sessions` tool for semantic session search
- [ ] Session summaries replaceable (regenerate, don't append)
- [ ] Session metadata tracks: message count, timestamp range, summary version

---

## File Structure

```
data/
├── memories.jsonl           # Individual messages (with session_id)
└── session_summaries.jsonl  # Session summaries with embeddings
```

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

```python
@dataclass
class SessionSummary:
    id: str                    # Unique summary ID
    session_id: str            # Links to messages
    timestamp: datetime        # When summary created
    message_range: tuple[int, int]  # (first_msg_idx, last_msg_idx) in session
    message_count: int         # How many messages summarized
    summary_text: str          # LLM-generated summary
    embedding: list[float]     # For semantic search
    version: int               # Increment on regeneration
    
    # For re-summarization decisions
    last_summarized_count: int  # Messages at last summary
```

**Storage format (session_summaries.jsonl):**
```json
{
  "id": "sum_abc123",
  "session_id": "sess_xyz789",
  "timestamp": "2026-02-19T16:30:00Z",
  "message_range": [0, 25],
  "message_count": 25,
  "summary_text": "User and Alfred discussed database architecture...",
  "embedding": [0.023, -0.156, ...],
  "version": 1,
  "last_summarized_count": 25
}
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
    
    # Check for existing summary
    existing = await get_session_summary(session.id)
    
    # Generate summary via LLM
    summary_text = await llm.summarize_conversation(messages)
    
    # Create embedding
    embedding = await embedder.create_embedding(summary_text)
    
    # Build summary (replace if exists)
    summary = SessionSummary(
        id=existing.id if existing else generate_id(),
        session_id=session.id,
        timestamp=now(),
        message_range=(0, len(messages)),
        message_count=len(messages),
        summary_text=summary_text,
        embedding=embedding,
        version=(existing.version + 1) if existing else 1,
        last_summarized_count=len(messages),
    )
    
    # Write to session_summaries.jsonl (append-only file, but conceptually replaces)
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
Searches individual messages.

```python
class SearchMemoriesTool:
    """Search individual memory entries."""
    
    async def execute(self, query: str, top_k: int = 5) -> ToolResult:
        query_embedding = await embedder.create_embedding(query)
        
        # Search memories.jsonl
        results = await search_by_similarity(
            query_embedding=query_embedding,
            index_path="data/memories.jsonl",
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
        
        # Search session_summaries.jsonl
        results = await search_by_similarity(
            query_embedding=query_embedding,
            index_path="data/session_summaries.jsonl",
            top_k=top_k,
        )
        
        return ToolResult(content=format_session_results(results))
```

**When to use which:**
- **search_memories:** Specific facts, commands, precise details
- **search_sessions:** Themes, projects, decisions, conversation flow

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
session_summaries_path = "data/session_summaries.jsonl"
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

---

## Dependencies

- ✅ #53 (Session System) — Message storage, session tracking
- ✅ #21 (M11: Learning System) — Context for summary generation
- Existing embedding client
- Existing cron infrastructure

---

## Vector Database Discussion

**Current approach (JSONL files):**
- Pros: Simple, no external dependencies, human-readable, easy to backup/inspect
- Cons: O(n) search (slow at scale), no filtering/complex queries, file locking issues

**When to consider a vector DB:**
- >100K memories (search becomes noticeably slow)
- Need metadata filtering ("find memories from last week about databases")
- Multiple Alfred instances (shared state)
- Need hybrid search (vector + keyword)

**Recommended if you switch:**
- **Chroma** — Embedded, zero-config, good for single-user local
- **SQLite + sqlite-vec** — Keep SQL, add vector index

**Not recommended:**
- Pinecone/Weaviate for local single-user (overkill)

**Verdict:** Stay with JSONL until you hit performance issues. The simplicity is worth it. Add SQLite + sqlite-vec when search latency becomes noticeable (>100ms for typical queries).
