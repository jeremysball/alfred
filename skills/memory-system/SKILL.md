# Alfred Memory System

## Overview

Alfred uses a **unified memory store** for all distilled memories:

```
data/memory/
└── memories.jsonl   # All memories with embeddings

MEMORY.md            # Curated long-term memories (separate)
```

Date is **metadata** (`timestamp` field), not structure. All memories live in one searchable space.

## How to Save Memories

### Use the `remember` Tool (Primary Method)

Alfred has a `remember` tool available in the main process. Use it to save memories:

```python
# Tool usage (automatic via agent loop)
remember(
    content="User prefers Python over JavaScript for backend work",
    importance=0.8,
    tags="preferences,coding"
)
```

**When to use:**
- User says "remember..." or "don't forget..."
- You learn important preferences ("I prefer X over Y")
- Key facts about projects, work, or life
- Information mentioned multiple times
- Anything useful for future conversations

**Parameters:**
- `content`: Specific, concise insight. "User has a dog named Max" not "User mentioned pets"
- `importance`: 0.0-1.0. Use 0.8+ for core preferences/identity, 1.0 for critical facts
- `tags`: Comma-separated categories like "preferences,work,family"

### Direct Store Access (For Distillation/Batch Operations)

For background processes or batch operations, use `MemoryStore.add_entries()`:

```python
from src.types import MemoryEntry
from datetime import datetime

entries = [
    MemoryEntry(
        timestamp=datetime.now(),
        role="system",
        content="User prefers Python over JavaScript for backend work",
        embedding=None,  # Will be generated
        importance=0.8,
        tags=["preferences", "coding"],
    ),
]
await memory_store.add_entries(entries)
```

**When to use direct access:**
- Distillation processes (end of day, conversation compaction)
- Batch imports or migrations
- Background memory maintenance

### Write to MEMORY.md (Curated Long-term)

For durable, high-value memories that should persist forever:

```python
# Direct file access for curated memories
await memory_store.append_curated_memory("User prefers dark mode for all apps")
```

**When to use MEMORY.md:**
- Core identity facts ("I work remotely from Portland")
- Important preferences ("I prefer tea over coffee")
- Project definitions that don't change
- Information needed 6+ months from now

## How to Search Memories

### Automatic Retrieval (Already Happens)

Relevant memories are **automatically injected** into your context via semantic search. You don't need to search manually.

The system:
1. Embeds the user's query
2. Searches all memories by cosine similarity
3. Ranks by hybrid score (similarity × recency × importance)
4. Injects top memories into your context under `## RELEVANT MEMORIES`

### Manual Search (If Needed)

```python
# Search all memories
results = await memory_store.search("coding preferences", top_k=10)

# Search with date filtering
results = await memory_store.search(
    "coding preferences",
    top_k=10,
    start_date=date(2026, 2, 1),
    end_date=date(2026, 2, 28),
)

# Search curated memories only
results = await memory_store.search_curated("important facts", top_k=5)
```

### Date Filtering

Since date is metadata, filter during search:

```python
# Get all entries from a specific day
feb_17_entries = await memory_store.filter_by_date(
    start_date=date(2026, 2, 17),
    end_date=date(2026, 2, 17),
)
```

## Memory Entry Structure

```python
class MemoryEntry:
    timestamp: datetime  # When recorded (includes date)
    role: "user" | "assistant" | "system"
    content: str         # The distilled insight
    embedding: list[float] | None  # Vector for semantic search
    importance: float    # 0.0 to 1.0
    tags: list[str]      # Categories
```

**Key point**: `timestamp` contains the date. No more `YYYY-MM-DD.md` files.

## Storage Format

### memories.jsonl

Each line is a JSON object:

```json
{"timestamp": "2026-02-17T14:30:00", "role": "system", "content": "User prefers Python", "embedding": [0.1, -0.2, ...], "importance": 0.8, "tags": ["preferences"]}
{"timestamp": "2026-02-17T14:31:00", "role": "system", "content": "User works remotely", "embedding": [0.2, -0.1, ...], "importance": 0.7, "tags": ["work"]]}
```

Benefits:
- Append-only (fast writes)
- Line-oriented (easy to iterate without loading all)
- JSON (human-readable, portable)

### MEMORY.md

Standard Markdown for human curation. Search parses it on-demand.

## Architecture Decision: Tools Over Skills

**We use tools, not skills, for memory operations.**

**Rationale:**
- Tools run in the main process with full context access
- No subprocess overhead or context serialization issues
- Simpler architecture: one tool registry, one execution model
- Agent already has tool-calling infrastructure

**Implications:**
- `remember` is a tool in `src/tools/remember.py`
- Memory operations appear in tool descriptions
- Agent decides when to call `remember` based on context
- No separate capability/skill system needed for memory

## Best Practices

1. **Prefer the `remember` tool**: Let the agent handle it naturally
2. **Be specific in content**: "User prefers FastAPI over Flask" > "User has opinions"
3. **Set importance honestly**: Not everything is 1.0
4. **Use tags for categorization**: Makes future filtering easier
5. **Let the store generate embeddings**: Pass `embedding=None`
6. **Use `iter_entries()` for large sets**: Memory-efficient iteration
7. **Date is just metadata**: Use `filter_by_date()` or date params in `search()`

## Performance Notes

- `add_entries()` batches embedding generation automatically
- `iter_entries()` streams from disk (no memory bloat)
- `search()` scores all entries linearly (FAISS/Annoy later if needed)
- Retrieval happens automatically before each response

## Failures

If embedding fails, fail fast. Don't store without embeddings—memories are useless for retrieval without vectors.
