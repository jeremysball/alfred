### search_sessions - Search Conversation History

Search through past conversation sessions for context and information.

**Parameters:**
- `query` (required): Search query describing what you're looking for
- `top_k` (optional): Maximum number of sessions to return (default: 3)
- `messages_per_session` (optional): Maximum messages to return per session (default: 3)
- `after` (optional): Filter sessions created after this date/time (ISO 8601 format)
- `before` (optional): Filter sessions created before this date/time (ISO 8601 format)

**When to use:**
- The user asks about a prior discussion, decision, or work session
- The request is time-bounded: "last Tuesday", "earlier today", "in March"
- Memory search was insufficient and you need conversation history
- You need to recover details from previous sessions rather than durable facts

**Examples:**

```python
search_sessions(query="OAuth callback debugging discussion")

search_sessions(query="why we chose SQLite", top_k=5)

search_sessions(
    query="deployment issues",
    after="2026-03-20",
)

search_sessions(query="*", top_k=10)
```

**Wildcard Mode (`*`):**
- Use `query="*"` to list sessions without semantic search
- Combine with `after` or `before` to browse a time window

**Tips:**
- Search memories first when you want durable facts or preferences
- Search sessions when you need prior discussion, chronology, or exact recall
- Use `after` and `before` to narrow noisy results
- If the user references earlier work and memory search comes up short, this is the right next step
