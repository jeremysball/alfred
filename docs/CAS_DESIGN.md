# Lock-Free JSONL Store with CAS (Compare-And-Swap)

## Overview

This module implements a **lock-free, atomic JSONL store** using Compare-And-Swap (CAS) semantics. It provides optimistic concurrency control without locks, eliminating deadlocks and reducing contention in concurrent scenarios.

## How CAS Prevents TOCTOU Bugs

### The TOCTOU Problem

**TOCTOU** (Time-of-Check-Time-of-Use) is a race condition where:

```python
# Classic TOCTOU bug
if file.exists():              # ← Check
    content = file.read()      # ← Use (file may have changed!)
```

Between the check and use, another process can modify the file, leading to:
- Lost updates
- Data corruption
- Inconsistent state

### CAS Solution

CAS makes the check and use **atomic**:

```python
# CAS approach - atomic check-and-act
expected_version = read_version()
new_content = transform(current_content)
success = write_if_version_matches(file, new_content, expected_version)

# If another writer changed the file, this fails and we retry
```

**Key insight:** CAS either succeeds completely or fails completely. There's no window for race conditions.

## Implementation Details

### Version Identification

Each file state has a `Version` computed from content hash:

```python
@dataclass(frozen=True)
class Version:
    content_hash: str  # Blake2b hash of file content
    mtime_ns: int      # Modification time (informational)
    size: int          # File size (informational)

    # Equality based ONLY on content_hash
    def __eq__(self, other) -> bool:
        return isinstance(other, Version) and self.content_hash == other.content_hash
```

**Why content hash?**
- Detects any content change, even if mtime/size are identical
- Cryptographically strong (Blake2b)
- 16-byte digest is fast and collision-resistant

### Atomic Write Operation

Writes use **temp-file + atomic rename** (POSIX guarantee):

```python
async def _write_content(content, expected_version):
    current_version = compute_version(path)

    # CAS check: fail if file changed since we read it
    if current_version != expected_version:
        raise CASConflictError()

    # Write to temp file
    temp_fd, temp_path = tempfile.mkstemp(...)
    os.write(temp_fd, content)
    os.fsync(temp_fd)  # Ensure durability
    os.close(temp_fd)

    # Atomic rename (POSIX: always atomic)
    os.replace(temp_path, target_path)

    # Sync directory for durability
    dir_fd = os.open(parent_dir, os.O_RDONLY | os.O_DIRECTORY)
    os.fsync(dir_fd)
```

### Retry Logic

When CAS conflicts occur, operations automatically retry:

```python
async def compare_and_swap(transform, max_retries=1000):
    for attempt in range(max_retries):
        version, records = read_file()
        new_records = transform(records)

        try:
            return await rewrite(new_records, expected_version=version)
        except CASConflictError:
            if attempt == max_retries - 1:
                raise
            # Retry with fresh read
            continue
```

**Why 1000 retries?**
- With exponential backoff equivalent (retries are cheap)
- High concurrency scenarios may need many retries
- Prevents infinite loops on persistent conflicts

## API Usage

### Basic Append

```python
store = CASStore(Path("data/events.jsonl"))

# Automatic retry on conflict
await store.append({"event": "user_login", "user_id": "123"})

# Or strict mode: fail immediately on conflict
version = await store.read_version()
try:
    await store.append(record, expected_version=version)
except CASConflictError:
    # Handle conflict manually
    pass
```

### Atomic Transform (Compare-and-Swap)

```python
# Atomic counter increment
def increment_counter(records):
    for r in records:
        if r.get("name") == "counter":
            r["value"] += 1
            return records
    # Counter doesn't exist, create it
    records.append({"name": "counter", "value": 1})
    return records

# Atomic: either succeeds with counter incremented, or fails
final_records, new_version = await store.compare_and_swap(increment_counter)
```

### Batch Operations

```python
# Atomic batch append (all or nothing)
await store.append_batch([
    {"id": 1, "data": "a"},
    {"id": 2, "data": "b"},
    {"id": 3, "data": "c"},
])
```

## Concurrency Guarantees

### What CAS Guarantees

1. **Atomicity:** Each write either succeeds completely or fails completely
2. **Consistency:** No partial writes visible to readers
3. **Conflict Detection:** Any concurrent modification is detected
4. **Automatic Retry:** Failed operations retry with fresh state

### What CAS Does NOT Guarantee

1. **Fairness:** In high contention, some writers may starve
2. **Ordering:** Writes may complete in different order than initiated
3. **Performance:** High contention causes many retries (thrashing)

### Performance Characteristics

| Scenario | Behavior |
|----------|----------|
| Single writer | No conflicts, maximum throughput |
| Low contention | Occasional retries, minimal overhead |
| High contention | Many retries, potential starvation |
| Many readers + 1 writer | Readers never block, writer may retry |

## Comparison with Lock-Based Approaches

| Aspect | CAS (Lock-Free) | Lock-Based |
|--------|-----------------|------------|
| **Deadlocks** | Impossible | Possible |
| **Priority inversion** | Impossible | Possible |
| **Contention overhead** | Retry on conflict | Queue waiting |
| **Scalability** | Excellent (no locks) | Limited (lock serialization) |
| **Determinism** | Non-deterministic retry count | Deterministic wait order |
| **Implementation** | More complex | Simpler |

## When to Use CAS

**Good for:**
- Infrequent writes, frequent reads
- Short, simple transformations
- Systems requiring deadlock-freedom
- Distributed systems (file locks don't work across NFS)

**Not ideal for:**
- High-write contention (thrashing)
- Long-running transactions
- Complex multi-file operations
- Guaranteed fairness requirements

## Error Handling

```python
from src.utils.cas_store import CASConflictError

try:
    await store.compare_and_swap(my_transform)
except CASConflictError as e:
    # Another process modified the file
    # Options:
    # 1. Retry manually with fresh read
    # 2. Abort and return error to user
    # 3. Log and continue (if acceptable)
    logger.warning(f"CAS conflict: expected {e.expected_version}, got {e.actual_version}")
```

## Testing

Run CAS-specific tests:

```bash
uv run pytest tests/test_cas_store.py -v
```

Key test scenarios:
- `test_cas_detects_concurrent_modification` - Verifies conflict detection
- `test_compare_and_swap_retry_on_conflict` - Verifies automatic retry
- `test_compare_and_swap_exhausts_retries` - Verifies retry limits
- `test_manual_conflict_recovery` - Demonstrates manual recovery

## Integration with Existing Code

The CAS store can replace the existing JSONL operations in:
- `src/memory.py` - Memory storage
- `src/cron/store.py` - Cron job persistence
- `src/session_storage.py` - Session message storage

Benefits:
- Eliminates lock files
- Prevents corruption on concurrent access
- Enables multi-process safety

## References

- **POSIX atomic rename:** `man 2 rename` - "If newpath exists, it will be atomically replaced"
- **Compare-And-Swap:** Herlihy & Shavit, "The Art of Multiprocessor Programming"
- **Optimistic Concurrency:** Kung & Robinson, "On Optimistic Methods for Concurrency Control"
