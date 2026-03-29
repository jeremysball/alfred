### search_memories - Search Saved Memories

Search through previously saved memories using semantic (meaning-based) search.

**Parameters:**
- `query` (required): Search query describing what you want to recall
- `top_k` (optional): Maximum number of results to return (default: 5)

**When to use:**
- Before asking the user to repeat information
- When the request refers to prior context, preferences, or ongoing work
- When the user says things like "again", "last time", "as before", "that project", or "what did I say about..."
- When you need durable facts rather than full conversation history

**Examples:**

```python
search_memories(query="communication preferences", top_k=5)

search_memories(query="database choice for the billing project")

search_memories(query="ongoing auth bug context")
```

**Tips:**
- Use natural language queries, not just keywords
- Search memories before asking the user to restate facts or preferences
- If memory search is not enough, fall back to `search_sessions`
- Search is semantic, so describe the concept you want to recall
