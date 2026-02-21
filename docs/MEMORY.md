# Alfred Memory System

This document explains Alfred's three-layer memory architecture to avoid confusion about where data lives and how it's searched.

---

## Quick Reference

| Layer | What | Where | Search Tool |
|-------|------|-------|-------------|
| **1. Curated Memory** | Facts Alfred explicitly remembers | `data/memory/memories.jsonl` | `search_memories` |
| **2. Session Summaries** | Narrative summaries of conversations | `data/sessions/{id}/summary.json` | `search_sessions` |
| **3. Session Messages** | Raw conversation messages | `data/sessions/{id}/messages.jsonl` | Contextual retrieval (PRD #77) |

---

## Storage Structure

```
data/
├── memory/
│   └── memories.jsonl              # Curated facts only
│
└── sessions/
    └── sess_abc123/                # One folder per session
        ├── messages.jsonl          # All session messages with embeddings
        └── summary.json            # Session summary + embedding
```

---

## Layer 1: Curated Memory

**What:** Facts that Alfred explicitly decides to remember using the `remember` tool.

**Where:** `data/memory/memories.jsonl`

**Characteristics:**
- Not automatic — Alfred chooses what to remember
- Has embeddings for semantic search
- Optional `session_id` field can link to a source session
- Searchable via `search_memories` tool

**Example entry:**
```json
{
  "timestamp": "2026-02-19T14:30:00Z",
  "role": "assistant",
  "content": "User prefers async/await over threads for Python concurrency",
  "embedding": [0.023, -0.156, ...],
  "tags": ["preference", "python"],
  "session_id": "sess_abc123",
  "entry_id": "a1b2c3d4e5f6g7h8"
}
```

---

## Layer 2: Session Summaries

**What:** LLM-generated narrative summaries of entire conversations.

**Where:** `data/sessions/{session_id}/summary.json`

**How created:** Cron job runs every 5 minutes and summarizes sessions that are either:
- Idle >30 minutes, OR
- Have 20+ new messages since last summary

**Characteristics:**
- Has embedding for semantic search
- Versions increment on re-summarization (replaced, not appended)
- Searchable via `search_sessions` tool

**Example:**
```json
{
  "id": "sum_abc123",
  "session_id": "sess_xyz789",
  "summary_text": "User and Alfred discussed database architecture options, decided on PostgreSQL with asyncpg...",
  "embedding": [0.023, -0.156, ...],
  "version": 1
}
```

---

## Layer 3: Session Messages

**What:** Raw conversation messages with embeddings.

**Where:** `data/sessions/{session_id}/messages.jsonl`

**Characteristics:**
- Every message has an embedding
- Enables contextual retrieval (PRD #77)
- Search within a session for higher precision

**Example entry:**
```json
{
  "idx": 0,
  "role": "user",
  "content": "Let's talk about database options",
  "timestamp": "2026-02-19T14:00:00Z",
  "embedding": [0.023, -0.156, ...]
}
```

---

## How Search Works

### search_memories (Layer 1)
Searches curated facts. Use for:
- Specific facts Alfred has remembered
- User preferences
- Commands, configurations, precise details

### search_sessions (Layer 2)
Searches session summaries. Use for:
- "What did we discuss about X?"
- Finding past conversations by theme
- Conversation arcs and decisions

### Contextual Retrieval (Layer 3, PRD #77)
Two-stage search:
1. Find relevant sessions via summary similarity
2. Search messages **within those sessions only**

This gives higher precision than searching all messages globally.

---

## Common Misconceptions

### ❌ "Messages go in memories.jsonl"
**Wrong.** `memories.jsonl` is for curated facts only. Messages live in session folders.

### ❌ "Session summaries are in a separate file"
**Wrong.** Summaries live in the session folder at `data/sessions/{id}/summary.json`.

### ❌ "session_id on MemoryEntry stores the message"
**Wrong.** `session_id` is just a link/reference. The actual messages are in the session folder.

### ❌ "All messages are automatically remembered"
**Wrong.** Alfred decides what to remember via the `remember` tool. Most messages stay in session storage, not curated memory.

---

## Implementation Status

| Component | Status | PRD |
|-----------|--------|-----|
| Curated Memory | ✅ Implemented | — |
| Session Summaries | 🔲 Planning | #76 |
| Session Messages | 🔲 Planning | #76 |
| Contextual Retrieval | 🔲 Planning | #77 |

---

## Related Documentation

- [PRD #76: Session Summarization with Cron](../prds/76-session-summarization-cron.md)
- [PRD #77: Contextual Retrieval System](../prds/77-contextual-retrieval-system.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md)
