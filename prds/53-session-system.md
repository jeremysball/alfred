# PRD: Conversation Session System

**Issue**: #53  
**Status**: Ready for Implementation  
**Priority**: High  
**Created**: 2026-02-18

---

## Problem Statement

Alfred has no conversation memory. Each Telegram message starts a fresh session—the LLM only sees the current user message, not the back-and-forth exchange. This makes coherent multi-turn conversation impossible. Users cannot refer to "what we just discussed" or build context over multiple messages.

---

## Solution Overview

Implement persistent conversation sessions with automatic summarization and semantic retrieval. Every conversation is stored, summarized after inactivity, and made searchable. The system loads relevant past conversations into context alongside the current session.

### Key Behaviors

1. **Active Session Tracking**: Current conversation held in memory, injected into every LLM call
2. **Automatic Persistence**: Sessions saved to JSONL on activity timeout (1 hour)
3. **Smart Summarization**: LLM extracts key topics/facts after session ends
4. **Semantic Retrieval**: Past conversation summaries searchable by current query
5. **Dual Storage**: Raw exchanges preserved + distilled insights extracted
6. **CLI Control**: Commands to start new session or resume old ones

---

## Technical Architecture

### Session Lifecycle

```
User Message → Load/Create Session → Inject History → LLM Response
                                    ↓
                              Store Exchange
                                    ↓
                    [1hr timeout] → Summarize → Embed → Save
```

### Data Schema

#### Active Session (In-Memory)
```python
@dataclass
class Session:
    session_id: str          # UUID
    chat_id: str             # Telegram chat ID
    created_at: datetime
    last_active: datetime
    exchanges: list[Exchange]  # Raw conversation
    status: "active" | "paused"

@dataclass
class Exchange:
    timestamp: datetime
    role: "user" | "assistant"
    content: str
```

#### Persistent Session Record (JSONL)
```json
{
  "session_id": "uuid",
  "chat_id": "123456",
  "created_at": "2026-02-18T10:00:00",
  "ended_at": "2026-02-18T11:30:00",
  "summary": "User discussed Python async patterns...",
  "summary_embedding": [0.1, -0.2, ...],
  "exchanges": [
    {"timestamp": "...", "role": "user", "content": "..."},
    {"timestamp": "...", "role": "assistant", "content": "..."}
  ],
  "key_facts": ["User prefers asyncio over threading"],
  "tags": ["python", "async"]
}
```

### File Structure

```
data/sessions/
├── active_sessions.jsonl      # Currently active sessions
└── archived/
    ├── 2026-02-18_sessions.jsonl
    ├── 2026-02-19_sessions.jsonl
    └── ...
```

---

## Context Injection Flow

```
User Query
    ↓
[1] Load active session for chat_id
[2] Get recent exchanges (last 10 turns)
[3] Embed query → search past session summaries
[4] Top 3 relevant past sessions → inject summaries
[5] Combine: System Prompt + Past Context + Active Session + Current Query
    ↓
LLM Response
    ↓
Store exchange to active session
    ↓
Check timeout → Summarize if > 1hr inactive
```

---

## Milestone Roadmap

| # | Milestone | Description | Success Criteria |
|---|-----------|-------------|------------------|
| 1 | **Session Data Model** | Create Session, Exchange dataclasses; JSONL serialization | Can create, save, load sessions |
| 2 | **Session Manager** | In-memory session tracking with TTL; auto-archive on timeout | Sessions persist 1hr, auto-summarize |
| 3 | **Summarization Engine** | LLM prompt to summarize session; extract key facts | Quality summaries with facts extraction |
| 4 | **Context Integration** | Inject active session + relevant past sessions into LLM context | LLM sees conversation history |
| 5 | **Telegram Integration** | Wire session manager to Telegram handler; per-chat sessions | Each chat has isolated session |
| 6 | **CLI Commands** | `/sessions` list, `/resume <id>`, `/newsession` commands | User can manage sessions |
| 7 | **Testing** | Unit tests for session lifecycle; integration test for full flow | >90% coverage, all tests pass |

---

## CLI Commands

```bash
# List recent sessions
alfred sessions
# Output:
# ID        Date        Summary
# sess_abc  2026-02-18  Discussed Python async patterns
# sess_def  2026-02-17  Planned vacation to Japan

# Resume a specific session
alfred resume sess_abc

# Force new session (even if active one exists)
alfred newsession

# Show session details
alfred session sess_abc
```

---

## Configuration

```python
SESSION_TIMEOUT_MINUTES = 60      # Auto-summarize after inactivity
SESSION_MAX_EXCHANGES = 100       # Force summarize after N turns
PAST_SESSIONS_IN_CONTEXT = 3      # Number of relevant past sessions
RECENT_EXCHANGES_IN_CONTEXT = 10  # Recent turns in active session
```

---

## Memory System Integration

### Relationship to Existing Memory

| System | Stores | Use Case |
|--------|--------|----------|
| **Session System** | Full conversations, summaries | Context for current conversation, finding relevant past chats |
| **MEMORY.md** | Curated long-term facts | Durable user preferences, persistent knowledge |
| **memories.jsonl** | Distilled facts from all interactions | Semantic search for specific facts |

### Data Flow

```
Conversation Ends
    ↓
Session Summarized
    ↓
├─→ Save to session archive (full conversation + summary)
└─→ Extract key facts → add to memories.jsonl
    ↓
Facts curated over time → update MEMORY.md
```

---

## Open Questions (Resolved)

**Q: How does this relate to the existing memory system?**  
A: Sessions handle conversation context; MEMORY.md handles curated facts. Session summaries feed into the memory pipeline.

**Q: What triggers session summarization?**  
A: 1 hour of inactivity OR 100 exchanges (configurable).

**Q: Can users manually control sessions?**  
A: Yes, via CLI commands to list, resume, or start fresh.

---

## Success Criteria

- [ ] Alfred remembers the current conversation across multiple messages
- [ ] Relevant past conversations appear in context automatically
- [ ] Sessions survive bot restarts
- [ ] Users can list and resume past sessions via CLI
- [ ] No perceptible latency increase (<100ms overhead)
- [ ] Storage grows linearly with actual conversations (not unbounded)

---

## Dependencies

- Existing memory system (memories.jsonl, embeddings)
- LLM provider for summarization
- Telegram chat ID for session isolation

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | JSONL storage for sessions | Consistent with existing memory system |
| 2026-02-18 | 1-hour timeout for summarization | Balances freshness with API efficiency |
| 2026-02-18 | Dual storage (raw + summary) | Enables both full replay and fast retrieval |
| 2026-02-18 | Per-chat session isolation | Telegram users don't share context |
