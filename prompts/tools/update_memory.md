### update_memory - Update an Existing Memory

Update the content or tags of a previously saved memory.

**Parameters:**
- `memory_id` (required): The unique ID of the memory to update
- `content` (optional): New content for the memory
- `tags` (optional): New comma-separated list of tags

**When to use:**
- Correcting outdated information
- Adding new details to an existing memory
- Changing tags for better organization
- Updating status (e.g., from "active" to "resolved")

**Examples:**

```python
# Update content
update_memory(
    memory_id="uuid-from-search",
    content="Now prefers Rust over Go for systems programming"
)

# Update tags to mark as resolved
update_memory(
    memory_id="uuid-from-search",
    tags="health,injury,resolved"
)

# Update both content and tags
update_memory(
    memory_id="uuid-from-search",
    content="Shoulder fully recovered, cleared for exercise",
    tags="health,injury,resolved"
)
```

**Tips:**
- Use `search_memories` first to find the memory_id
- Only specify fields you want to change
- Memory ID is returned from `search_memories` or `remember`
- Creates a new version of the memory (old version preserved)
