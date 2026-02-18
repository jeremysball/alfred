# PRD: Remove Importance Score, Add Similarity to Search Output

**Issue**: #57  
**Status**: Ready for Implementation  
**Priority**: Medium  
**Created**: 2026-02-18

---

## Problem Statement

The memory system has two friction points:

1. **Importance score adds complexity**: Every memory has an `importance` field (0.0-1.0) that must be set, stored, and factored into search scoring. Users don't actually use or care about this value.

2. **No visibility into search relevance**: When `search_memories` returns results, users can't see why those memories were selected. The similarity score is calculated but hidden.

**User Impact**: Extra cognitive load managing importance scores, and confusion about why certain memories appear in search results.

---

## Solution Overview

### 1. Remove Importance Score
- Delete `importance` field from `MemoryEntry` dataclass
- Remove from storage (JSONL format)
- Remove from search scoring hybrid algorithm
- Remove from tool parameters where applicable

### 2. Expose Similarity in Search Results
- Add `similarity` field to search output
- Display as percentage (e.g., "95% match")
- Helps users understand result ranking

---

## Current vs New Behavior

### Current (With Importance)
```
User: Remember that I like pizza

LLM: [calls remember with content="User likes pizza", importance=0.6]
→ Stored with importance 0.6

User: What do I like?

LLM: [calls search_memories with query="food preferences"]
→ Returns:
   - User likes pizza (importance: 0.6)
```

### New (Without Importance, With Similarity)
```
User: Remember that I like pizza

LLM: [calls remember with content="User likes pizza"]
→ Stored without importance

User: What do I like?

LLM: [calls search_memories with query="food preferences"]
→ Returns:
   - User likes pizza (92% match)
```

---

## Technical Architecture

### Data Model Changes

```python
# BEFORE
@dataclass
class MemoryEntry:
    id: str
    content: str
    role: str
    timestamp: datetime
    importance: float  # ← REMOVE THIS
    embedding: list[float] | None
    tags: list[str]

# AFTER
@dataclass
class MemoryEntry:
    id: str
    content: str
    role: str
    timestamp: datetime
    embedding: list[float] | None
    tags: list[str]
```

### Search Result Format

```python
# BEFORE (in search_memories output)
"- [2026-02-18] User likes pizza (importance: 0.6, id: abc123)"

# AFTER (in search_memories output)  
"- [2026-02-18] User likes pizza (92% match, id: abc123)"
```

### Search Scoring Changes

```python
# BEFORE (hybrid scoring in MemorySearcher)
def _hybrid_score(self, memory: MemoryEntry, similarity: float) -> float:
    age_days = (datetime.now() - memory.timestamp).days
    recency = math.exp(-age_days / self.recency_half_life)
    return similarity * 0.5 + recency * 0.3 + memory.importance * 0.2

# AFTER (simpler scoring)
def _hybrid_score(self, memory: MemoryEntry, similarity: float) -> float:
    age_days = (datetime.now() - memory.timestamp).days
    recency = math.exp(-age_days / self.recency_half_life)
    return similarity * 0.6 + recency * 0.4  # Higher weight on similarity
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/types.py` | Remove `importance` from `MemoryEntry` |
| `src/memory.py` | Remove importance handling, storage, defaults |
| `src/search.py` | Update scoring weights, return similarity |
| `src/tools/remember.py` | Remove importance parameter |
| `src/tools/search_memories.py` | Add similarity to output format |
| `src/tools/update_memory.py` | Remove importance parameter |
| `data/memory/memories.jsonl` | Migration: remove importance field |

---

## Migration Strategy

### Existing Memory Files
When loading old memories with importance:
1. Load and ignore the `importance` field
2. Save new memories without importance
3. Graceful backward compatibility (one-time)

### Code Migration
Update all references:
- [ ] `MemoryEntry` dataclass
- [ ] MemoryStore.create_entry()
- [ ] MemoryStore.update_entry()
- [ ] RememberTool parameter
- [ ] UpdateMemoryTool parameter
- [ ] Search output formatting
- [ ] Hybrid scoring algorithm
- [ ] All tests

---

## Milestone Roadmap

| # | Milestone | Description | Success Criteria |
|---|-----------|-------------|------------------|
| 1 | **Update MemoryEntry** | Remove importance field from dataclass | Tests updated, dataclass clean |
| 2 | **Update MemoryStore** | Remove importance from CRUD operations | create/update work without importance |
| 3 | **Update search scoring** | Remove importance from hybrid score, boost similarity weight | Search results ranked correctly |
| 4 | **Update RememberTool** | Remove importance parameter | Tool works without importance param |
| 5 | **Update UpdateMemoryTool** | Remove importance parameter | Tool works without importance param |
| 6 | **Update SearchMemoriesTool** | Add similarity to output format | Output shows "X% match" |
| 7 | **Add migration logic** | Handle loading old memories with importance | Backward compatible |
| 8 | **Update tests** | All tests pass without importance | >90% coverage |
| 9 | **Update documentation** | Remove importance references from docs | Clean documentation |

---

## Tool Signature Changes

### RememberTool
```python
# BEFORE
async def execute(
    self,
    content: str,
    importance: float = 0.5,  # ← REMOVE
    tags: list[str] | None = None,
)

# AFTER
async def execute(
    self,
    content: str,
    tags: list[str] | None = None,
)
```

### UpdateMemoryTool
```python
# BEFORE
async def execute(
    self,
    memory_id: str,
    content: str | None = None,
    importance: float | None = None,  # ← REMOVE
    tags: list[str] | None = None,
)

# AFTER
async def execute(
    self,
    memory_id: str,
    content: str | None = None,
    tags: list[str] | None = None,
)
```

### SearchMemoriesTool Output
```python
# BEFORE
"- [2026-02-18] Memory content (importance: 0.6, id: abc123)"

# AFTER  
"- [2026-02-18] Memory content (92% match, id: abc123)"
```

---

## Search Output Format

### Current Format
```
## RELEVANT MEMORIES

- [2026-02-18] User lives in San Francisco (importance: 0.6, id: f926ff7f)
- [2026-02-18] User's name is Jaz (importance: 0.7, id: 33705b40)
```

### New Format
```
## RELEVANT MEMORIES

- [2026-02-18] User lives in San Francisco (95% match, id: f926ff7f)
- [2026-02-18] User's name is Jaz (87% match, id: 33705b40)
```

---

## Success Criteria

- [ ] Importance field removed from MemoryEntry
- [ ] Importance parameter removed from RememberTool
- [ ] Importance parameter removed from UpdateMemoryTool
- [ ] Search results display similarity percentage
- [ ] Search scoring works without importance (similarity + recency only)
- [ ] Old memory files load correctly (backward compatibility)
- [ ] All tests updated and passing
- [ ] No references to importance in codebase

---

## Dependencies

- Memory store system
- Search/indexing system
- Tool registry

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | Remove importance entirely | Adds complexity without user benefit |
| 2026-02-18 | Boost similarity weight to 0.6 | More intuitive ranking |
| 2026-02-18 | Show similarity as percentage | More readable than 0-1 float |
| 2026-02-18 | One-time backward compatibility | Graceful migration of existing data |
