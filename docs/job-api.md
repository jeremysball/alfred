# Job API Reference

Jobs run in a restricted sandbox environment with limited access to Alfred's systems. This document describes what's available to job code and how it differs from tool access.

## Security Model

Jobs execute arbitrary user-submitted Python code. To maintain security and stability:

- Jobs run in a restricted namespace with limited builtins
- Jobs cannot access Alfred's memory store, tools, or internal state directly
- Jobs communicate through a controlled `ExecutionContext` API
- Jobs are isolated from the main application and each other

## Available Functions

| Function | Status | Description |
|----------|--------|-------------|
| `notify(message)` | ✅ Available | Send a notification message to the user (Telegram or CLI) |
| `store_get(key)` | ❌ Not implemented | Retrieve a value from the job's persistent key-value store |
| `store_set(key, value)` | ❌ Not implemented | Save a value to the job's persistent key-value store |
| `print()` | ✅ Available | Output to job logs (captured and stored with execution history) |

### Built-in Python Functions

Jobs have access to a safe subset of Python builtins:

```python
# Types
len, str, int, float, bool, list, dict, set, tuple

# Iteration
range, enumerate, zip, map, filter, reversed, sorted

# Math
sum, min, max, abs, round, pow, divmod

# Utilities
format, repr, any, all, hasattr, getattr, setattr
isinstance, issubclass, type

# Encoding
chr, ord, hex, bin, oct

# Exceptions (all standard exceptions available)
Exception, ValueError, TypeError, KeyError, etc.
```

## Job vs Tool Capabilities

Understanding the distinction between jobs and tools is important for deciding where to implement functionality.

### Tools (Used by Alfred)

- **Access Level**: Full access to Alfred's subsystems
- **Execution**: Runs in Alfred's main context during conversation
- **Capabilities**:
  - Read/write files
  - Access MemoryStore (search, add, update memories)
  - Control the scheduler (register, approve, pause jobs)
  - Execute bash commands
  - Return results directly to the conversation

**Example tool usage:**
```python
# Alfred calls tools during conversation
result = await read_tool.execute(path="todo.md")
# Result goes directly into conversation
```

### Jobs (Run by Scheduler)

- **Access Level**: Restricted to ExecutionContext API only
- **Execution**: Runs independently in the background
- **Capabilities**:
  - Perform scheduled tasks
  - Print output (logged to execution history)
  - Store small amounts of data via store_get/store_set (when implemented)
  - Send notifications via notify() (when implemented)
- **Limitations**:
  - Cannot access files directly (unless code does file I/O)
  - Cannot call Alfred's tools
  - Cannot modify memories directly
  - Cannot send messages to users (pending notifier implementation)

**Example job code:**
```python
# User-submitted job code
async def run():
    print("Checking system status...")
    # Process something
    await notify("System check complete!")
```

## Common Patterns

### Logging Output

Use `print()` to capture information that will be stored in execution history:

```python
async def run():
    print(f"Job started at {datetime.now()}")
    # Do work
    print(f"Job completed, processed {count} items")
```

### Error Handling

Jobs should handle errors gracefully:

```python
async def run():
    try:
        # Risky operation
        result = await fetch_data()
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}")
        await notify(f"Job failed: {e}")
```

### State Persistence

When `store_get`/`store_set` are implemented:

```python
async def run():
    # Get previous count
    count = store_get("processed_count") or 0
    
    # Process new items
    new_items = await fetch_new_items()
    count += len(new_items)
    
    # Save updated count
    store_set("processed_count", count)
    print(f"Total processed: {count}")
```

## Future Enhancements

The following features are planned but not yet implemented:

1. **Persistent KV Store**: Implement `store_get`/`store_set` with durable storage
2. **Memory Bridge**: Potential API for jobs to queue memory additions (subject to approval)
3. **HTTP Client**: Safe HTTP requests for API calls (with allowlist)

## Related Documentation

- [Cron Jobs](cron-jobs.md) - Overview of the cron system and job lifecycle
- [Notifier Architecture](notifier.md) - How user notifications work (or will work)
