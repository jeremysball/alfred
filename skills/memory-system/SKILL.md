# Alfred Memory System

## Overview

Alfred uses a **unified memory store** for all distilled memories:

```
memory/
└── memories.jsonl   # All memories with embeddings

MEMORY.md            # Curated long-term memories (separate)
```

Date is **metadata** (`timestamp` field), not structure. All memories live in one searchable space.

## When to Write Memories

### Add to Unified Store (via `MemoryStore.add_entries()`)

**When**: Run the distillation process:
- At the end of each day
- Before compacting a long conversation
- When explicitly asked to "remember this"

**What to store**: Distilled insights as `MemoryEntry` objects:
- Key facts learned about the user
- Decisions made and why
- Project context and status
- Preferences expressed

Example:
```python
entries = [
    MemoryEntry(
        timestamp=datetime.now(),
        role="user",
        content="User prefers Python over JavaScript for backend work",
        embedding=None,  # Will be generated
        importance=0.8,
        tags=["preferences", "coding"],
    ),
]
await memory_store.add_entries(entries)
```

### Write to MEMORY.md (via `MemoryStore.write_curated_memory()` or `append_curated_memory()`)

**When**: For durable, high-value memories:
- Core preferences ("I prefer dark mode")
- Important facts ("User has a dog named Max")
- Project definitions ("Project X is a web API")

**Guideline**: If you'd want to know this 6 months from now, put it in MEMORY.md.

## How to Search Memories

### Unified Store Search

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
```

### Curated Memory Search

```python
results = await memory_store.search_curated("important facts", top_k=5)
```

### Date Filtering (No Daily Files!)

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
{"timestamp": "2026-02-17T14:30:00", "role": "user", "content": "I prefer Python", "embedding": [0.1, -0.2, ...], "importance": 0.8, "tags": ["preferences"]}
{"timestamp": "2026-02-17T14:31:00", "role": "assistant", "content": "Noted.", "embedding": [0.2, -0.1, ...], "importance": 0.5, "tags": []}
```

Benefits:
- Append-only (fast writes)
- Line-oriented (easy to iterate without loading all)
- JSON (human-readable, portable)

### MEMORY.md

Standard Markdown for human curation. Search parses it on-demand.

## Distillation Process

**Purpose**: Convert raw conversation into searchable `MemoryEntry` units.

**Flow**:
1. Read conversation history
2. Extract key facts, decisions, context
3. Create `MemoryEntry` objects (with `timestamp`, `importance`, `tags`)
4. Call `memory_store.add_entries(entries)`

**Rule of thumb**: One insight per entry. Don't dump entire conversations.

## Best Practices

1. **Let the store generate embeddings**: Pass `embedding=None`, the store handles batching
2. **Use `iter_entries()` for large sets**: Memory-efficient iteration
3. **Date is just metadata**: Use `filter_by_date()` or date params in `search()`
4. **Be specific in content**: "User prefers FastAPI over Flask" > "User has opinions"
5. **Set importance honestly**: Not everything is 1.0

## Performance Notes

- `add_entries()` batches embedding generation automatically
- `iter_entries()` streams from disk (no memory bloat)
- `search()` scores all entries (will add index later if needed)
- For now: linear scan is fine, we can add FAISS/Annoy later

## Failures

If embedding fails, fail fast. Don't store without embeddings - memories are useless for retrieval without vectors.
