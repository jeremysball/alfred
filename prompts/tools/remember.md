### remember - Save a Memory

Save a useful fact, preference, or piece of context for future retrieval.

**Parameters:**
- `content` (required): The distilled fact or insight to remember
- `tags` (optional): Comma-separated list of category tags (for example `preferences,work,health`)
- `permanent` (optional): Mark as permanent to skip normal expiration

**When to use:**
- Durable user preferences likely to matter again
- Project decisions, stable context, or recurring technical setup
- Personal facts or milestones that will help in future conversations
- Ongoing issues, goals, or patterns likely to come back

**Avoid using it for:**
- Every transient error or one-off detail
- Raw logs or noisy pasted output
- Duplicate facts already saved elsewhere
- Facts that belong in always-loaded identity files unless the user wants that update

**Examples:**

```python
remember(
    content="Prefers concise responses with direct recommendations",
    tags="preferences,communication",
)

remember(
    content="Using PostgreSQL for the billing service",
    tags="project,database,billing",
)

remember(
    content="Currently debugging OAuth callback failures in staging",
    tags="project,debugging,oauth,active",
)
```

**Tips:**
- Prefer fewer, higher-value memories
- Write concise, searchable content
- Use `permanent=True` only for facts that should outlive normal memory turnover
- Search memories before creating duplicates
