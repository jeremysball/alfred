# PRD: Conversation Session System

**Issue**: #53
**Status**: Ready for Implementation
**Priority**: High
**Created**: 2026-02-18
**Updated**: 2026-02-22
**Depends on**: #54 (✅ Complete - In-Memory Session Storage)
**Related**: #76 (Session Summarization), #77 (Contextual Retrieval)

---

## Problem Statement

Alfred has no conversation memory. Each Telegram message starts a fresh session—the LLM only sees the current user message, not the back-and-forth exchange. This makes coherent multi-turn conversation impossible. Users cannot refer to "what we just discussed" or build context over multiple messages.

---

## Solution Overview

Implement persistent conversation sessions with explicit user control and automatic summarization. Every conversation is stored with embeddings, summarized after idle time, and made searchable. Users explicitly create and resume sessions.

### Key Behaviors

1. **Explicit Session Control**: `/new` creates session, `/resume <id>` continues previous session
2. **Immediate Persistence**: Every message stored with embedding immediately (durability)
3. **Auto-Summarization**: LLM summarizes session after 30 min idle (cron job)
4. **Forever Retention**: Sessions persist indefinitely, never auto-deleted
5. **Triple-Layer Memory**: Curated facts + session summaries + session messages (see PRD #77)
6. **Unified Chat ID**: Both Telegram and CLI use `chat_id` for session isolation

---

## Technical Architecture

### Session Lifecycle

```
/new command → Create new session → Set as active for chat_id
                                        ↓
User Message → Load active session → Inject history → LLM Response
                                        ↓
                                 Store Message with Embedding
                                        ↓
                         Append to data/sessions/{id}/messages.jsonl
                                        ↓
                    [30 min idle] → Cron summarizes → summary.json (via PRD #76)

/resume <id> → Load session → Set as active → Continue conversation
```

**Key principle**: Sessions are user-controlled, not auto-detected. No automatic session boundaries.

### Data Schema

#### Session
```python
@dataclass
class Session:
    session_id: str          # Telegram thread ID OR CLI-generated UUID
    created_at: datetime
    last_active: datetime
    status: "active" | "idle"  # idle = summarized, still resumable
```

**Session ID assignment:**
- **Telegram**: `session_id` = Telegram thread ID (implicit, automatic)
- **CLI**: `session_id` = UUID, controlled via `/new` and `/resume`

#### Message (with embedding)
```python
@dataclass
class Message:
    idx: int                 # Position in file (local to current.jsonl or archive.jsonl)
    role: "user" | "assistant"
    content: str
    timestamp: datetime
    embedding: list[float] | None  # None until async embedding completes
```

**Indexing**: Each file (`current.jsonl`, `archive.jsonl`) has its own indices starting from 0. Archive represents messages before the last summary point.

#### Session Summary (separate file)
```python
@dataclass
class SessionSummary:
    session_id: str
    summary_text: str
    embedding: list[float]   # For finding relevant sessions
    message_count: int
    created_at: datetime
    last_summarized: datetime
```

### File Structure

```
data/
├── memory/
│   └── memories.jsonl           # Layer 1: Curated facts Alfred remembers
│
└── sessions/
    ├── current.json             # CLI current session_id (persists across restarts)
    │
    └── {session_id}/            # One folder per session
        ├── meta.json            # Session metadata
        ├── current.jsonl        # Recent messages (loaded for context)
        ├── archive.jsonl        # Older messages (post-compaction)
        └── summary.json         # Layer 2: Summary + embedding (PRD #76)
```

#### Session Metadata (meta.json)
```json
{
  "session_id": "sess_abc123",
  "created_at": "2026-02-22T10:00:00Z",
  "last_active": "2026-02-22T12:30:00Z",
  "message_count": 47,
  "current_count": 20,
  "archive_count": 27
}
```

**Context loading**: Always load from `current.jsonl`. Compaction (future) moves older messages to `archive.jsonl`, keeping context bounded.

**Embedding**: Simple `asyncio.create_task()` after message written. No queue infrastructure.

**SessionManager**: Keep as singleton (per PRD #54).

---

## Context Injection Flow

```
User Query
    ↓
[1] Get session_id: Telegram thread ID OR CLI current session
[2] If session folder doesn't exist → auto-create, inform user
[3] Load messages from data/sessions/{session_id}/current.jsonl
[4] Combine: System Prompt + Session Messages + Current Query
    ↓
LLM Response
    ↓
[5] Write message to current.jsonl (no embedding yet)
[6] asyncio.create_task(): Generate embedding, update message record
```

**No auto-injection of past sessions**: The LLM uses `search_sessions` tool (PRD #77) when it needs relevant past context. Past sessions are not automatically injected into context.

---

## Milestone Roadmap

| # | Milestone | Description | Success Criteria |
|---|-----------|-------------|------------------|
| 1 | **Session Data Model** | ✅ Complete in PRD #54 | `Session`, `Message` dataclasses in `src/session.py` |
| 2 | **Session Manager V2** | ✅ Complete | Multi-session manager with per-session folders, `SessionStorage` class |
| 3 | **Message Persistence** | ✅ Complete | `current.jsonl` per session, async embedding |
| 4 | **CLI Commands** | ✅ Complete | `/new`, `/resume`, `/sessions`, `/session` commands implemented |
| 5 | **Context Integration** | ✅ Complete | Session messages injected into LLM context via `ContextBuilder` |
| 6 | **Telegram Integration** | Wire session manager to Telegram handler | Per-chat sessions via Telegram chat_id |
| 7 | **Testing** | ✅ Complete | 564 tests passing, session storage and CLI tested |

**Note**: Summarization via cron (PRD #76) and contextual retrieval (PRD #77) are separate PRDs that build on this foundation.

---

## CLI Commands

**Telegram**: Session is tied to thread ID. No commands needed — user is always in that thread's session.

**CLI**: User manages multiple sessions:

```bash
# Create a new session
/new
# Output: Created session sess_abc123

# List all CLI sessions
/sessions
# Output:
# ID            Created     Last Active  Messages  Summary
# sess_abc123   2026-02-22  2 hours ago  47        Discussed Python async patterns
# sess_def456   2026-02-21  1 day ago    23        Planned vacation to Japan

# Resume a specific session
/resume sess_abc123
# Output: Resumed session sess_abc123 (47 messages)

# Show current session
/session
# Output: Current session: sess_abc123 (started 2 hours ago, 47 messages)
```

**First-time user**: Auto-create session + inform: *"Created session sess_abc. Use /new to start fresh or /sessions to resume a past conversation."*

---

## Configuration

```toml
[session]
idle_minutes = 30              # Summarize after idle (PRD #76 cron)
sessions_dir = "data/sessions" # Session folder storage
```

**Note**: Secrets (API keys, tokens) go in environment variables, not config file.

---

## Memory System Integration

### Triple-Layer Architecture (with PRDs #76, #77)

| Layer | Location | Stores | Search Pattern |
|-------|----------|--------|----------------|
| **Global Memory** | `data/memory/memories.jsonl` | Curated facts | Semantic similarity |
| **Session Summaries** | `data/sessions/{id}/summary.json` | Narrative arcs | Semantic similarity |
| **Session Messages** | `data/sessions/{id}/messages.jsonl` | Every message | Contextual (session-scoped) |

### Data Flow

```
During Conversation (every message):
    User Message → LLM Response → Store to current.jsonl → Async embed

When Session Idle (30 min, via cron PRD #76):
    Generate Summary → Embed → Write to summary.json

When Compaction Needed (future):
    Move older messages from current.jsonl → archive.jsonl
```

**This PRD (#53)**: Session storage, message persistence, `/new`, `/resume`, `/sessions`
**PRD #76**: Cron-based summarization after idle
**PRD #77**: Contextual retrieval across layers

---

## Open Questions

**Q: What happens on first message if no session exists?**
A: Alfred prompts user to `/new` or `/sessions`. No auto-creation.

**Q: Can multiple sessions be active simultaneously?**
A: One active session per `chat_id`. Different chats (Telegram) or CLI have independent active sessions.

**Q: How are sessions ordered in `/sessions` output?**
A: By `last_active` descending (most recent first).

---

## Success Criteria

- [x] `/new` creates a new session with unique ID
- [x] `/resume <id>` loads and continues a previous session
- [x] `/sessions` lists all sessions with summaries
- [ ] Every message stored with embedding in `current.jsonl`
- [x] Sessions persist across bot restarts
- [ ] CLI and Telegram both use `chat_id` system
- [ ] No perceptible latency increase (<100ms overhead)

---

## Dependencies

- ✅ PRD #54 (In-Memory Session Storage) - Complete
- Existing memory system (memories.jsonl, embeddings)
- LLM provider for embeddings on each message
- Telegram chat ID for session isolation

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | JSONL storage for sessions | Consistent with existing memory system |
| 2026-02-18 | Dual storage (raw + summary) | Enables both full replay and fast retrieval |
| 2026-02-18 | Per-chat session isolation | Telegram users don't share context |
| 2026-02-22 | Explicit session control (`/new`, `/resume`) for CLI | User decides when to start fresh |
| 2026-02-22 | Sessions persist forever | Never lose conversation history |
| 2026-02-22 | Per-session folder structure | Enables contextual retrieval (PRD #77) |
| 2026-02-22 | Every message with embedding (async) | Semantic search without latency impact |
| 2026-02-22 | Config file, not env vars | Secrets in env, config in TOML |
| 2026-02-22 | No auto-injection of past sessions | LLM uses tools to fetch relevant context |
| 2026-02-22 | Telegram thread ID = session_id | Natural mapping, no management needed |
| 2026-02-22 | CLI uses UUID session_ids with `/new`/`/resume` | Multiple sessions over time |
| 2026-02-22 | Session discovery via folder scan | Simple, no index file to maintain |
| 2026-02-22 | First-time user: auto-create + inform | No friction, but user knows what happened |
| 2026-02-22 | CLI current session persisted in `current.json` | Survives restarts |
| 2026-02-22 | `meta.json` per session for metadata | Fast access to created_at, last_active, message_count |
| 2026-02-22 | `current.jsonl` + `archive.jsonl` split | Compaction keeps context bounded |
| 2026-02-22 | Local indices per file | Archive starts from summary, separate index space |
| 2026-02-22 | Async embedding via `asyncio.create_task()` | No queue infrastructure needed |
| 2026-02-22 | SessionManager remains singleton | Simplicity, per PRD #54 |
