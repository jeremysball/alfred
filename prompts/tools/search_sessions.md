### search_sessions - Search Conversation History

Search through past conversation sessions for context and information.

**Parameters:**
- `query` (required): Search query describing what you're looking for
- `limit` (optional): Maximum number of sessions to return (default: 5)

**When to use:**
- Looking for context from previous work sessions
- Finding decisions made in past conversations
- Recalling technical discussions
- Locating previously written code or documentation

**Examples:**

```python
# Search for previous work on a feature
search_sessions(query="MessagePanel implementation details")

# Search for architectural decisions
search_sessions(query="Why did we choose SQLite over PostgreSQL")

# Search with limit
search_sessions(query="CHIP-8 emulator progress", limit=3)
```

**Tips:**
- Uses semantic search (finds conceptually related sessions)
- Returns session summaries and IDs
- Good for finding context from days/weeks ago
- Searches across all your conversation history
