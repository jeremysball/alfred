### search_sessions - Search Conversation History

Search through past conversation sessions for context and information.

**Parameters:**
- `query` (required): Search query describing what you're looking for
- `top_k` (optional): Maximum number of sessions to return (default: 3)
- `messages_per_session` (optional): Maximum messages to return per session (default: 3)
- `after` (optional): Filter sessions created after this date/time (ISO 8601 format)
- `before` (optional): Filter sessions created before this date/time (ISO 8601 format)

**When to use:**
- Looking for context from previous work sessions
- Finding decisions made in past conversations
- Recalling technical discussions
- Locating previously written code or documentation
- Narrowing results to a specific time period
- Listing all recent sessions (use wildcard `*`)

**Examples:**

```python
# Search for previous work on a feature
search_sessions(query="MessagePanel implementation details")

# Search for architectural decisions
search_sessions(query="Why did we choose SQLite over PostgreSQL")

# Search with more results
search_sessions(query="CHIP-8 emulator progress", top_k=5)

# Search only sessions from the last week
search_sessions(
    query="deployment issues",
    after="2024-03-17"
)

# Search sessions from a specific date range
search_sessions(
    query="API design decisions",
    after="2024-01-01",
    before="2024-03-01"
)

# Search with datetime (ISO 8601 format)
search_sessions(
    query="critical bug fix",
    after="2024-03-20T10:00:00"
)

# List all recent sessions (wildcard mode)
search_sessions(query="*")

# List sessions from the last week
search_sessions(
    query="*",
    after="2024-03-17",
    top_k=10
)
```

**Wildcard Mode (`*`):**
- Use `query="*"` to list all sessions without semantic search
- Useful for browsing recent conversation history
- Combine with `after`/`before` to list sessions from a specific time period
- Combine with `top_k` to control how many sessions to return
- Wildcards accepted: `*`, `*.*`, `all`, `ALL`

**Date Filter Formats:**
- Date only: `"2024-03-20"` (searches from midnight UTC)
- Date and time: `"2024-03-20T10:00:00"` or `"2024-03-20T10:00:00Z"`
- With timezone: `"2024-03-20T10:00:00-05:00"`

**Tips:**
- Uses semantic search (finds conceptually related sessions)
- Returns session summaries and IDs
- Good for finding context from days/weeks ago
- Searches across all your conversation history
- Use `after` to exclude old sessions and focus on recent work
- Use `before` to find historical context before a specific point
- Combine `after` and `before` to search within a specific period
- Use wildcard `*` as the query to browse all sessions chronologically
