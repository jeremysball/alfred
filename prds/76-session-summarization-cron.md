# PRD: Session Summarization with Cron

## Overview

**Issue**: #76
**Parent**: #10 (Alfred - The Rememberer)
**Depends On**: #53 (Session System), #21 (M11: Learning System)
**Status**: Ready for Implementation
**Priority**: High
**Created**: 2026-02-19
**Branch**: `feature/prd-76-session-summarization-cron`

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
- [ ] `data/sessions/{session_id}/summary.json` storage with embeddings
- [ ] Cron job for automatic summarization (30 min idle OR 20 msg threshold)
- [ ] `search_sessions` tool for semantic session search
- [ ] Session summaries replaceable (regenerate, don't append)
- [ ] Session metadata tracks: message count, timestamp range, summary version

---

## Implementation Status

**Current Phase:** Ready to start  
**Branch:** `feature/prd-76-session-summarization-cron`  
**Estimated Tasks:** 79 atomic commits  
**Approach:** Test-first TDD with conventional commits

---

## Detailed Execution Plan

### Phase 1: Session ID Tagging Infrastructure (8 tasks)

#### Session ID Data Model

- [ ] **Test:** `test_memory_entry_has_session_id_field()` — verify MemoryEntry accepts session_id
  - **Commit:** `test(memory): verify MemoryEntry accepts session_id field`
  
- [ ] **Implement:** Add `session_id: str` field to `MemoryEntry` dataclass
  - **Commit:** `feat(memory): add session_id field to MemoryEntry dataclass`

- [ ] **Test:** `test_assign_session_id_creates_new_when_none()` — new session when no current session
  - **Commit:** `test(session): verify assign_session_id creates new session when none exists`

- [ ] **Test:** `test_assign_session_id_continues_within_threshold()` — continues existing session within 30 min gap
  - **Commit:** `test(session): verify session continues within 30 minute threshold`

- [ ] **Test:** `test_assign_session_id_creates_new_after_threshold()` — new session after 30 min idle
  - **Commit:** `test(session): verify new session created after 30 minute idle threshold`

- [ ] **Implement:** Create `assign_session_id()` function with 30-minute threshold logic
  - **Commit:** `feat(session): implement assign_session_id with 30min threshold`

#### Session Metadata Tracking (Extend `SessionMeta`)

- [ ] **Test:** `test_session_meta_tracks_first_message_time()` — verify first_message_time field
  - **Commit:** `test(session): verify SessionMeta tracks first_message_time`

- [ ] **Test:** `test_session_meta_tracks_last_summarized_count()` — verify last_summarized_count field
  - **Commit:** `test(session): verify SessionMeta tracks last_summarized_count`

- [ ] **Test:** `test_session_meta_tracks_summary_version()` — verify summary_version field
  - **Commit:** `test(session): verify SessionMeta tracks summary_version`

- [ ] **Implement:** Add `first_message_time`, `last_summarized_count`, `summary_version` to `SessionMeta`
  - **Commit:** `feat(session): extend SessionMeta with summarization tracking fields`

---

### Phase 2: Session Storage Infrastructure (8 tasks)

#### Directory Structure

- [ ] **Test:** `test_sessions_dir_created_on_init()` — verify `data/sessions/` directory created
  - **Commit:** `test(storage): verify sessions directory created on initialization`

- [ ] **Implement:** Create `ensure_sessions_dir()` function in storage module
  - **Commit:** `feat(storage): create ensure_sessions_dir for session storage`

- [ ] **Test:** `test_session_folder_created_for_new_session()` — verify `{session_id}/` folder created
  - **Commit:** `test(storage): verify session folder created for new session`

- [ ] **Implement:** Create `create_session_folder(session_id)` function
  - **Commit:** `feat(storage): implement create_session_folder for session isolation`

#### Session Messages Storage

- [ ] **Test:** `test_store_session_message_writes_to_jsonl()` — verify message written to `{session_id}/messages.jsonl`
  - **Commit:** `test(storage): verify session messages written to jsonl`

- [ ] **Implement:** Create `store_session_message(session_id, message)` function
  - **Commit:** `feat(storage): implement store_session_message for session persistence`

- [ ] **Test:** `test_get_session_messages_returns_all_messages()` — verify retrieval returns list
  - **Commit:** `test(storage): verify get_session_messages returns all messages`

- [ ] **Implement:** Create `get_session_messages(session_id)` function
  - **Commit:** `feat(storage): implement get_session_messages retrieval`

---

### Phase 3: Session Summary Storage (10 tasks)

#### Summary Data Model

- [ ] **Test:** `test_session_summary_has_required_fields()` — verify SessionSummary dataclass fields
  - **Commit:** `test(summary): verify SessionSummary has all required fields`

- [ ] **Implement:** Create `SessionSummary` dataclass (id, session_id, timestamp, message_range, message_count, summary_text, embedding, version, last_summarized_count)
  - **Commit:** `feat(summary): create SessionSummary dataclass`

- [ ] **Test:** `test_session_summary_serialization_roundtrip()` — verify to/from JSON works
  - **Commit:** `test(summary): verify SessionSummary serialization roundtrip`

- [ ] **Implement:** Add `to_json()` and `from_json()` methods to SessionSummary
  - **Commit:** `feat(summary): add JSON serialization for SessionSummary`

#### Summary Storage Operations

- [ ] **Test:** `test_store_summary_writes_to_json_file()` — verify writes to `{session_id}/summary.json`
  - **Commit:** `test(summary): verify summary written to json file`

- [ ] **Implement:** Create `store_summary(summary)` function
  - **Commit:** `feat(summary): implement store_summary persistence`

- [ ] **Test:** `test_get_summary_returns_existing_summary()` — verify retrieval works
  - **Commit:** `test(summary): verify get_summary returns existing summary`

- [ ] **Test:** `test_get_summary_returns_none_when_missing()` — verify None when no summary
  - **Commit:** `test(summary): verify get_summary returns None when missing`

- [ ] **Implement:** Create `get_summary(session_id)` function
  - **Commit:** `feat(summary): implement get_summary retrieval`

- [ ] **Test:** `test_store_summary_increments_version()` — verify version increments on replacement
  - **Commit:** `test(summary): verify summary version increments on replacement`

- [ ] **Implement:** Update `store_summary()` to increment version based on existing summary
  - **Commit:** `feat(summary): implement version increment on summary replacement`

---

### Phase 4: Summary Generation (10 tasks)

#### LLM Summarization

- [ ] **Test:** `test_summarize_conversation_calls_llm()` — verify llm.summarize_conversation invoked with messages
  - **Commit:** `test(llm): verify summarize_conversation calls LLM with messages`

- [ ] **Implement:** Create `summarize_conversation(messages)` LLM interface function
  - **Commit:** `feat(llm): implement summarize_conversation interface`

- [ ] **Test:** `test_summarize_conversation_returns_summary_text()` — verify returns string summary
  - **Commit:** `test(llm): verify summarize_conversation returns summary text`

- [ ] **Implement:** Add LLM prompt and parsing for conversation summarization
  - **Commit:** `feat(llm): add conversation summarization prompt`

#### Summary Generation Pipeline

- [ ] **Test:** `test_generate_session_summary_creates_embedding()` — verify embedding created for summary
  - **Commit:** `test(summary): verify generate_session_summary creates embedding`

- [ ] **Implement:** Create `generate_session_summary(session)` async function
  - **Commit:** `feat(summary): implement generate_session_summary pipeline`

- [ ] **Test:** `test_generate_session_summary_uses_existing_summary_id()` — verify ID reuse on regeneration
  - **Commit:** `test(summary): verify generate_session_summary reuses existing summary ID`

- [ ] **Implement:** Update `generate_session_summary` to check for existing and reuse ID
  - **Commit:** `feat(summary): reuse existing summary ID on regeneration`

- [ ] **Test:** `test_generate_session_summary_sets_correct_message_range()` — verify message_range accurate
  - **Commit:** `test(summary): verify generate_session_summary sets correct message range`

- [ ] **Implement:** Set message_range to (0, len(messages)) in generate_session_summary
  - **Commit:** `feat(summary): set full message range in summary generation`

---

### Phase 5: Cron Job - Session Detection (8 tasks)

#### Active Session Detection

- [ ] **Test:** `test_get_active_sessions_returns_sessions_with_messages()` — verify filters to active only
  - **Commit:** `test(cron): verify get_active_sessions returns only active sessions`

- [ ] **Implement:** Create `get_active_sessions()` function to scan sessions directory
  - **Commit:** `feat(cron): implement get_active_sessions scanning`

- [ ] **Test:** `test_get_active_sessions_includes_message_counts()` — verify metadata loaded
  - **Commit:** `test(cron): verify get_active_sessions includes message counts`

- [ ] **Implement:** Load session metadata (total_messages, last_message_time) in get_active_sessions
  - **Commit:** `feat(cron): load session metadata in get_active_sessions`

#### Summarization Trigger Logic

- [ ] **Test:** `test_should_summarize_returns_true_when_idle_threshold_met()` — 30 min idle triggers
  - **Commit:** `test(cron): verify should_summarize true when idle > 30 min`

- [ ] **Test:** `test_should_summarize_returns_true_when_message_threshold_met()` — 20 new messages triggers
  - **Commit:** `test(cron): verify should_summarize true when 20+ new messages`

- [ ] **Test:** `test_should_summarize_returns_false_when_below_thresholds()` — neither threshold met
  - **Commit:** `test(cron): verify should_summarize false when below thresholds`

- [ ] **Implement:** Create `should_summarize(session)` function with threshold logic
  - **Commit:** `feat(cron): implement should_summarize threshold logic`

---

### Phase 6: Cron Job - Main Loop (10 tasks)

#### Cron Job Implementation

- [ ] **Test:** `test_summarize_sessions_job_calls_get_active_sessions()` — verify session scanning
  - **Commit:** `test(cron): verify summarize_sessions_job scans active sessions`

- [ ] **Implement:** Create `summarize_sessions_job(config)` async function skeleton
  - **Commit:** `feat(cron): create summarize_sessions_job skeleton`

- [ ] **Test:** `test_summarize_sessions_job_filters_by_should_summarize()` — verify filtering logic
  - **Commit:** `test(cron): verify summarize_sessions_job filters by should_summarize`

- [ ] **Implement:** Add filtering loop in summarize_sessions_job using should_summarize
  - **Commit:** `feat(cron): add should_summarize filtering to job`

- [ ] **Test:** `test_summarize_sessions_job_generates_summary_for_eligible()` — verify generation called
  - **Commit:** `test(cron): verify summarize_sessions_job generates summaries`

- [ ] **Implement:** Call generate_session_summary for eligible sessions
  - **Commit:** `feat(cron): wire summary generation into cron job`

#### Cron Registration

- [ ] **Test:** `test_cron_job_registered_with_interval()` — verify cron system knows about job
  - **Commit:** `test(cron): verify cron job registered with 5 minute interval`

- [ ] **Implement:** Register `summarize_sessions_job` in cron system with 5-minute interval
  - **Commit:** `feat(cron): register summarize_sessions_job with 5min interval`

- [ ] **Test:** `test_cron_interval_configurable()` — verify interval reads from config
  - **Commit:** `test(config): verify cron interval configurable via config`

- [ ] **Implement:** Add `[session]` config section with `cron_interval_minutes` setting
  - **Commit:** `feat(config): add session.cron_interval_minutes configuration`

---

### Phase 7: Search Sessions Tool (12 tasks)

#### Session Summary Search

- [ ] **Test:** `test_search_session_summaries_finds_similar()` — verify embedding similarity search
  - **Commit:** `test(search): verify search_session_summaries finds similar summaries`

- [ ] **Implement:** Create `search_session_summaries(query_embedding, sessions_dir, top_k)` function
  - **Commit:** `feat(search): implement search_session_summaries embedding search`

- [ ] **Test:** `test_search_session_summaries_returns_top_k()` — verify limits results
  - **Commit:** `test(search): verify search_session_summaries respects top_k limit`

- [ ] **Implement:** Add top_k limiting to search_session_summaries
  - **Commit:** `feat(search): add top_k limiting to session summary search`

#### SearchSessionsTool

- [ ] **Test:** `test_search_sessions_tool_exists()` — verify tool class exists
  - **Commit:** `test(tools): verify SearchSessionsTool class exists`

- [ ] **Implement:** Create `SearchSessionsTool` class with name, description
  - **Commit:** `feat(tools): create SearchSessionsTool class`

- [ ] **Test:** `test_search_sessions_tool_creates_embedding()` — verify query embedding created
  - **Commit:** `test(tools): verify SearchSessionsTool creates query embedding`

- [ ] **Implement:** Add embedding creation in SearchSessionsTool.execute()
  - **Commit:** `feat(tools): add embedding creation to SearchSessionsTool`

- [ ] **Test:** `test_search_sessions_tool_calls_search()` — verify search_session_summaries invoked
  - **Commit:** `test(tools): verify SearchSessionsTool calls search_session_summaries`

- [ ] **Implement:** Wire search_session_summaries into SearchSessionsTool.execute()
  - **Commit:** `feat(tools): wire search into SearchSessionsTool`

- [ ] **Test:** `test_search_sessions_tool_formats_results()` — verify results formatted nicely
  - **Commit:** `test(tools): verify SearchSessionsTool formats results`

- [ ] **Implement:** Add result formatting (session_id, timestamp, summary preview) to tool
  - **Commit:** `feat(tools): add result formatting to SearchSessionsTool`

- [ ] **Test:** `test_search_sessions_tool_registered()` — verify tool available to Alfred
  - **Commit:** `test(tools): verify SearchSessionsTool registered with tool system`

- [ ] **Implement:** Register SearchSessionsTool in tool registry
  - **Commit:** `feat(tools): register SearchSessionsTool in tool registry`

---

### Phase 8: Integration & Configuration (8 tasks)

#### Configuration

- [ ] **Test:** `test_config_has_session_section()` — verify [session] config section loads
  - **Commit:** `test(config): verify session config section loads`

- [ ] **Implement:** Add `[session]` config section with all settings (summarize_idle_minutes, summarize_message_threshold, cron_interval_minutes)
  - **Commit:** `feat(config): add session configuration section`

- [ ] **Test:** `test_config_default_values_correct()` — verify default values match PRD (30, 20, 5)
  - **Commit:** `test(config): verify session config default values`

- [ ] **Implement:** Set default config values (30 min idle, 20 msg, 5 min cron)
  - **Commit:** `feat(config): set session config default values`

#### End-to-End Integration

- [ ] **Test:** `test_message_written_gets_session_id()` — verify full flow: message → session_id → storage
  - **Commit:** `test(integration): verify message flow assigns session_id and stores`

- [ ] **Implement:** Wire session_id assignment into message storage pipeline
  - **Commit:** `feat(integration): wire session_id into message storage pipeline`

- [ ] **Test:** `test_cron_finds_and_summarizes_idle_session()` — verify full cron flow end-to-end
  - **Commit:** `test(integration): verify cron finds and summarizes idle session`

- [ ] **Implement:** Integration test verifying full cron flow
  - **Commit:** `feat(integration): end-to-end cron summarization test`

---

### Phase 9: Documentation & Cleanup (5 tasks)

- [ ] **Docs:** Update PRD progress section with completed items
  - **Commit:** `docs(prd): update PRD #76 progress with completed work`

- [ ] **Refactor:** Review and consolidate duplicate code between memory and session storage
  - **Commit:** `refactor(storage): consolidate shared storage utilities`

- [ ] **Test:** Run full test suite `uv run pytest` — all tests pass
  - **Commit:** `chore(tests): verify full test suite passes`

- [ ] **Lint:** Run `uv run ruff check src/` — no issues
  - **Commit:** `style: fix linting issues`

- [ ] **Type Check:** Run `uv run basedpyright src/` — no type errors
  - **Commit:** `types: fix type checking issues`

---

### Execution Summary

| Phase | Tasks | Commits | Focus |
|-------|-------|---------|-------|
| Phase 1 | 8 | 8 | Session ID infrastructure |
| Phase 2 | 8 | 8 | Storage infrastructure |
| Phase 3 | 10 | 10 | Summary data model & storage |
| Phase 4 | 10 | 10 | LLM summarization pipeline |
| Phase 5 | 8 | 8 | Session detection logic |
| Phase 6 | 10 | 10 | Cron job implementation |
| Phase 7 | 12 | 12 | SearchSessions tool |
| Phase 8 | 8 | 8 | Config & integration |
| Phase 9 | 5 | 5 | Cleanup & verification |
| **Total** | **79** | **79** | **Complete implementation** |

### Commit Message Pattern

```
<type>(<scope>): <description>

Types: test, feat, refactor, docs, style, types, chore
Scopes: memory, session, storage, summary, llm, cron, search, tools, config, integration
```

### Daily Workflow

```
1. Pick next unchecked task from PRD
2. Write test (Red)
3. Run test: uv run pytest <test_file>::<test_name> -v
4. Implement minimum code (Green)
5. Run test again to verify pass
6. Commit with conventional commit format
7. Check off task in PRD
8. Repeat
```

---

## File Structure

**Existing structure (PRD #53):**
```
data/
├── memory/
│   └── memories.jsonl           # Curated facts (can link to sessions via session_id)
└── sessions/
    ├── current.json             # CLI current session_id
    └── {session_id}/
        ├── meta.json            # Session metadata (created_at, last_active, status)
        ├── current.jsonl        # Recent messages with embeddings
        ├── tokens.jsonl         # Token count deltas (append-only)
        └── archive.jsonl        # Older messages (post-compaction)
```

**After PRD #76 implementation:**
```
data/
├── memory/
│   └── memories.jsonl           # Curated facts (can link to sessions via session_id)
└── sessions/
    ├── current.json             # CLI current session_id
    └── {session_id}/
        ├── meta.json            # Session metadata
        ├── current.jsonl        # Recent messages with embeddings
        ├── tokens.jsonl         # Token count deltas
        ├── archive.jsonl        # Archived messages
        └── summary.json         # NEW: Session summary + embedding
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

Summaries live alongside their session's messages in `data/sessions/{session_id}/summary.json`.

```python
@dataclass
class SessionSummary:
    id: str                    # Unique summary ID
    session_id: str            # Links to session folder
    timestamp: datetime        # When summary created
    message_range: tuple[int, int]  # (first_msg_idx, last_msg_idx) in session
    message_count: int         # How many messages summarized
    summary_text: str          # LLM-generated summary
    embedding: list[float]     # For semantic search
    version: int               # Increment on regeneration
    
    # For re-summarization decisions
    last_summarized_count: int  # Messages at last summary
```

**Storage format (data/sessions/{session_id}/summary.json):**

Uses single JSON file (not JSONL) since each session has exactly one summary that gets replaced on regeneration:

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

**Storage approach:** JSON file that gets overwritten on regeneration (version increments).

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
    
    # Write to session folder (data/sessions/{session_id}/summary.json)
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
sessions_dir = "data/sessions"   # Each session is a folder
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
| 2026-03-06 | Use existing `sessions/{id}/` structure | PRD #53 already established session folders |
| 2026-03-06 | Store summary as JSON (not JSONL) | Single summary per session, replaced on regeneration |
| 2026-03-06 | Keep JSONL for messages, JSON for summary | Aligns with existing storage patterns (current.jsonl, meta.json) |
| 2026-03-06 | Extend `SessionMeta` instead of new `SessionMetadata` | Single metadata file per session, persists across resumes |
| 2026-03-06 | 30-min threshold only triggers summarization, not session end | Session stays active indefinitely; threshold is for cron only |

---

## Dependencies

- ✅ #53 (Session System) — Message storage, session tracking
- ✅ #21 (M11: Learning System) — Context for summary generation
- Existing embedding client
- Existing cron infrastructure

---

## Future: Triple-Layer Memory Architecture

This PRD implements dual search (curated memories + session summaries). PRD #77 adds **per-session message embeddings** for contextual retrieval:

1. **Curated Memory** (data/memory/memories.jsonl) — Facts Alfred explicitly remembers
2. **Session Summaries** (data/sessions/{id}/summary.json) — Narrative arcs with embeddings ← THIS PRD
3. **Session Messages** (data/sessions/{id}/messages.jsonl) — Individual messages with embeddings

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
