### remember - Save a Memory

Save an important fact, preference, or context to the memory store for future retrieval.

**Parameters:**
- `content` (required): The distilled insight or fact to remember
- `tags` (optional): Comma-separated list of category tags (e.g., "preferences,work,health")
- `permanent` (optional): Mark as permanent (skip 90-day TTL), default: false

**When to use:**
- User mentions personal facts (family, preferences, life events)
- Technical decisions or project context
- Recurring patterns, struggles, or goals
- **DO NOT wait for permission - remember proactively**

**Examples:**

```python
# Remember a preference
remember(
    content="Prefers Go over Kotlin for job search due to higher remote pay",
    tags="preferences,job-search"
)

# Remember a personal milestone
remember(
    content="Son was born on March 15, 2026",
    tags="family,milestone,permanent",
    permanent=True
)

# Remember current struggle
remember(
    content="Currently struggling with async Rust lifetimes",
    tags="rust,learning,active"
)

# Remember project context
remember(
    content="CHIP-8 emulator being built in C for learning",
    tags="project,chip8,c,learning"
)

# Remember health info
remember(
    content="Has shoulder injury affecting exercise, in physical therapy",
    tags="health,injury,active"
)
```

**Tips:**
- Use concise, searchable content
- Add relevant tags for categorization
- Mark truly permanent facts (birthdays, core preferences) with `permanent=True`
- Default to remembering - don't ask "should I remember this?"
- Content is searchable via `search_memories`
