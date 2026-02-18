# PRD: Conversation Session System

**Issue**: #53  
**Status**: Ready for Implementation  
**Priority**: High  
**Created**: 2026-02-18
**Depends on**: #54 (✅ Complete - In-Memory Session Storage)

---

## Problem Statement

Alfred has no conversation memory. Each Telegram message starts a fresh session—the LLM only sees the current user message, not the back-and-forth exchange. This makes coherent multi-turn conversation impossible. Users cannot refer to "what we just discussed" or build context over multiple messages.

---

## Solution Overview

Implement persistent conversation sessions with automatic summarization and semantic retrieval. Every conversation is stored, summarized after inactivity, and made searchable. The system loads relevant past conversations into context alongside the current session.

### Key Behaviors

1. **Active Session Tracking**: Current conversation held in memory, injected into every LLM call
2. **Immediate Persistence**: Every exchange appended to sessions.jsonl immediately (durability)
3. **Smart Summarization**: LLM extracts key topics/facts after 1 hour of inactivity
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
                         Append to sessions.jsonl (durability)
                                    ↓
                    [1hr timeout] → Summarize → Embed → Update record
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
data/
├── memories.jsonl       # Curated facts extracted from all sessions
└── sessions.jsonl       # All sessions (active + archived)
```

---

## Context Injection Flow

```
User Query
    ↓
[1] Load active session for chat_id
[2] Get all exchanges from active session (no limit - fills context)
[3] Embed query → search past session summaries
[4] Top 3 relevant past sessions → inject summaries
[5] Combine: System Prompt + Past Context + Active Session + Current Query
    ↓
LLM Response
    ↓
Store exchange to active session
    ↓
Append to sessions.jsonl (immediate durability)
    ↓
Check timeout → Summarize if > 1hr inactive
```

**Note on Long Conversations**: Active session exchanges fill the available context window without artificial limits. Token budget management and compaction (intelligent summarization of older exchanges) will be implemented in a future milestone.

---

## Milestone Roadmap

| # | Milestone | Description | Success Criteria |
|---|-----------|-------------|------------------|
| 1 | **Session Data Model** | ✅ Complete in PRD #54 | `Session`, `Message` dataclasses in `src/session.py` |
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
# Note: No limit on recent exchanges - fills context until token budget hit
# Compaction (future milestone) will handle long conversations
```

---

## Memory System Integration

### Relationship to Existing Memory

| System | Stores | Use Case | Status |
|--------|--------|----------|--------|
| **Session System** | Full conversations, summaries | Context for current conversation, finding relevant past chats | **New** |
| **memories.jsonl** | Curated facts from all interactions | Long-term curated knowledge + semantic search | **Active** - populated from session key_facts |

### Data Flow

```
During Conversation (every message):
    User Message → LLM Response → Append exchange to sessions.jsonl

When Session Ends (1hr timeout):
    Session Summarized
        ↓
    ├─→ Update session record in sessions.jsonl with summary + embedding
    └─→ Extract key facts → add to memories.jsonl
```

- **sessions.jsonl**: Complete session history (written immediately per message), summaries added on timeout
- **memories.jsonl**: Curated facts extracted from sessions (long-term knowledge store)

---

## Open Questions (Resolved)

**Q: How does this relate to the existing memory system?**  
A: Sessions handle conversation context. memories.jsonl is the curated long-term knowledge store. Key facts extracted from session summaries feed into memories.jsonl.

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

- ✅ PRD #54 (In-Memory Session Storage) - Complete
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
