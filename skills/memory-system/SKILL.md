# Alfred Memory System

## Overview

Alfred has two memory layers for maintaining context across conversations:

1. **Daily Logs** (`memory/YYYY-MM-DD.md`) - Distilled daily memories
2. **MEMORY.md** - Curated long-term memories

## When to Write Memories

### Write to Daily Logs (via `MemoryStore.write_daily_log`)

**When**: Run the distillation process:
- At the end of each day
- Before compacting a long conversation
- When explicitly asked to "remember this"

**What to store**: Distilled insights, not raw chat. Turn conversations into:
- Key facts learned about the user
- Decisions made and why
- Project context and status
- Preferences expressed

Example daily log entry:
```markdown
## 14:32 - Assistant
User is building a Python CLI tool called "alfred-prd". They prefer async/await patterns and use `uv` for dependency management.

<!-- metadata: {'importance': 0.8, 'tags': ['coding', 'python', 'preferences']} -->
```

### Write to MEMORY.md (via `MemoryStore.write_curated_memory` or `append_curated_memory`)

**When**: For durable, high-value memories that should persist forever:
- User's core preferences ("I prefer dark mode")
- Important facts ("User has a dog named Max")
- Project definitions ("Project X is a web API")
- Relationship context

**Guideline**: If you'd want to know this 6 months from now, put it in MEMORY.md.

## How to Search Memories

Use `MemoryStore.search_memories(query, top_k=10)` to find relevant context.

**When to search**:
- At the start of each conversation to load context
- When the user asks "remember when...?"
- When you need background on a topic

**The search returns**: `MemoryEntry` objects with:
- `content` - The distilled memory text
- `timestamp` - When it was recorded
- `importance` - 0.0 to 1.0
- `tags` - Category tags
- `embedding` - Vector for similarity

## Memory Entry Structure

```python
class MemoryEntry:
    timestamp: datetime  # When recorded
    role: "user" | "assistant" | "system"
    content: str         # The distilled insight
    embedding: list[float]  # Vector for semantic search
    importance: float    # 0.0 to 1.0
    tags: list[str]      # Categories
```

## Distillation Process

**Purpose**: Convert raw conversation into searchable memory units.

**How**: 
1. Read conversation history
2. Extract key facts, decisions, context
3. Create MemoryEntry objects with embeddings
4. Write to daily log via `write_daily_log`

**Rule of thumb**: One insight per entry. Don't dump entire conversations.

## Best Practices

1. **Be specific**: "User prefers FastAPI over Flask" > "User has opinions"
2. **Include context**: Record *why* decisions were made
3. **Tag appropriately**: Helps with organization and filtering
4. **Set importance honestly**: Not everything is 1.0
5. **Distill, don't copy**: Summarize insights, don't paste chat logs

## Failures

If embedding fails, fail fast. Don't store without embeddings - memories are useless for retrieval without vectors.
