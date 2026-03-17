# PRD: Persistent Memory Context with LRU Eviction

**GitHub Issue**: [#135](https://github.com/jeremysball/alfred/issues/135)

---

## Problem Statement

Currently, Alfred searches memories fresh every turn based on the current query embedding. This creates several issues:

1. **Lost Context**: Memories discovered relevant in earlier turns disappear in later turns if the query embedding shifts
2. **Inconsistent Experience**: The model may "forget" important user preferences mid-conversation
3. **Wasted Relevance Work**: Semantic search results from previous turns are discarded even if still relevant

**Example scenario**: 
- Turn 1: User says "Remember I use Vim" → memory saved, appears in context
- Turn 2: User asks "What's the weather?" → Vim memory not in context (low relevance to weather query)
- Turn 3: User asks "How do I edit this file?" → Vim memory should still be there, but may not be found

---

## Solution Overview

Implement a **persistent memory context** that:
- Keeps memories loaded for the entire session
- Automatically adds new `remember` tool results to active context
- Evicts memories only when configurable limits are reached
- Uses LRU (Least Recently Accessed) eviction policy
- Persists until session ends (`/new` command)

---

## Configuration

Add to `config.toml`:

```toml
[memory_context]
# Maximum number of memories to keep in active context
max_memories = 50

# Maximum tokens allocated to memory section (0 = no limit)
max_memory_tokens = 8000

# When true, new memories from 'remember' tool auto-add to context
auto_add_new_memories = true

# Eviction strategy: "lru" (least recently accessed) or "fifo" (first in, first out)
eviction_strategy = "lru"
```

**Defaults**:
- `max_memories`: 50
- `max_memory_tokens`: 8000 (approximately 2000-3000 tokens worth of memory text)
- `auto_add_new_memories`: true
- `eviction_strategy`: "lru"

---

## Technical Design

### Active Memory Cache

Create new class `ActiveMemoryCache` in `src/alfred/memory/active_cache.py`:

```python
@dataclass
class CachedMemory:
    entry: MemoryEntry
    last_accessed: datetime
    access_count: int

class ActiveMemoryCache:
    """LRU cache for memories actively in context."""
    
    def __init__(
        self,
        max_memories: int = 50,
        max_tokens: int = 8000,
        strategy: str = "lru"
    ) -> None:
        self._cache: dict[str, CachedMemory] = {}
        self._max_memories = max_memories
        self._max_tokens = max_tokens
        self._strategy = strategy
    
    def add(self, memory: MemoryEntry) -> bool:
        """Add memory to cache, evicting if necessary. Returns True if added."""
        
    def mark_accessed(self, entry_id: str) -> None:
        """Mark memory as accessed (updates LRU)."""
        
    def get_active_memories(self) -> list[MemoryEntry]:
        """Get all memories currently in cache."""
        
    def evict_if_needed(self, new_memory_tokens: int = 0) -> list[str]:
        """Evict memories if limits exceeded. Returns evicted IDs."""
```

### Integration Points

1. **Session Manager**: Add `ActiveMemoryCache` to `Session` class
   - One cache per session
   - Cleared on `/new` command

2. **Context Building**: Modify `ContextBuilder.build_context()`
   - Start with cached memories instead of empty
   - Add new search results to cache
   - Evict if limits exceeded

3. **Remember Tool**: Modify `RememberTool.execute_stream()`
   - After saving memory, add to session's active cache
   - Only if `auto_add_new_memories` is true

4. **Context Display**: Enhance `/context` command
   - Show indicator for "active" vs "available" memories
   - Display cache stats (size, limit, strategy)

### Memory Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│  SESSION START                                               │
│  Active cache: empty                                         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  USER MESSAGE + SEARCH                                       │
│  1. Search finds memories A, B, C                           │
│  2. Add to active cache                                      │
│  3. Include in system prompt                                 │
│  Active cache: [A, B, C]                                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  NEXT TURN - DIFFERENT QUERY                                 │
│  1. Search finds memories C, D, E                           │
│  2. C already in cache (mark accessed)                      │
│  3. Add D, E to cache                                        │
│  4. Cache: [A, B, C, D, E] → evict if needed                │
│  5. Include all in system prompt                             │
│  Active cache: [A, B, C, D, E] (limited by config)          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  USER: "Remember that I..." (remember tool)                  │
│  1. Save memory F to database                                │
│  2. Add F to active cache (auto-add enabled)                │
│  3. Include F in current context immediately                │
│  Active cache: [A, B, C, D, E, F]                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  LIMIT REACHED → LRU EVICTION                               │
│  1. A not accessed for longest time → evict                 │
│  Active cache: [B, C, D, E, F]                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  /new COMMAND (session end)                                  │
│  Active cache: cleared                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

- [ ] Memories persist across turns within a session
- [ ] New memories from `remember` tool appear immediately in context
- [ ] LRU eviction removes least recently accessed memories when limits hit
- [ ] Configuration options work via `config.toml`
- [ ] `/context` shows active vs total memory counts
- [ ] Memory count limit enforced (default 50)
- [ ] Token limit enforced (default 8000 tokens)
- [ ] `/new` command clears active memory cache

---

## Milestones

### M1: Core Active Memory Cache
- [ ] Create `ActiveMemoryCache` class with LRU logic
- [ ] Add to `Session` class
- [ ] Unit tests for cache operations

### M2: Context Integration
- [ ] Modify `ContextBuilder` to use active cache
- [ ] Integrate with `assemble_with_search()`
- [ ] Test persistence across multiple turns

### M3: Remember Tool Integration
- [ ] Auto-add new memories to active cache
- [ ] Respect `auto_add_new_memories` config
- [ ] Test immediate appearance in context

### M4: Configuration & Limits
- [ ] Add config section to `Config` class
- [ ] Load from `config.toml`
- [ ] Implement limit checking and eviction
- [ ] Test eviction strategies

### M5: Context Command Enhancement
- [ ] Update `/context` output with active indicator
- [ ] Show cache stats (size, limit, strategy)
- [ ] Integration test

### M6: Session Lifecycle
- [ ] Clear cache on `/new` command
- [ ] Persist cache in session storage (optional future enhancement)
- [ ] End-to-end test

---

## Out of Scope (Future Considerations)

- Persisting active cache across sessions (would require session resumption with memory state)
- Multiple eviction strategies beyond LRU/FIFO
- Per-memory TTL (time-based eviction)
- Manual memory pinning/unpinning commands
