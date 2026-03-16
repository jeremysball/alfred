### forget - Delete a Memory

Permanently delete a memory from the store.

**Parameters:**
- `memory_id` (required): The unique ID of the memory to delete

**When to use:**
- Removing incorrect information
- Deleting outdated or irrelevant memories
- Cleaning up mistakes

**Examples:**

```python
# Delete a specific memory
forget(memory_id="uuid-from-search")
```

**Tips:**
- Use `search_memories` first to find the memory_id
- Deletion is permanent (cannot be undone)
- Consider `update_memory` instead if the information just needs correction
