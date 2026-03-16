### search_memories - Search Saved Memories

Search through previously saved memories using semantic (meaning-based) search.

**Parameters:**
- `query` (required): Search query - describe what you're looking for
- `limit` (optional): Maximum number of results to return (default: 10)

**When to use:**
- Before asking the user to repeat information
- Looking for context from previous sessions
- Finding related facts about a topic
- Recalling user preferences or history

**Examples:**

```python
# Search for preferences
search_memories(query="What programming languages does Jaz prefer?")

# Search for project context
search_memories(query="CHIP-8 emulator project details")

# Search for health information
search_memories(query="Shoulder injury status")

# Search with limit
search_memories(query="Job search strategy", limit=5)

# Search for family info
search_memories(query="Son birthday family details")
```

**Tips:**
- Use natural language queries, not just keywords
- Searches are semantic (finds related concepts, not just exact matches)
- Always search BEFORE asking "what did you say about..."
- Returns most relevant results first
- If no results, then ask the user
