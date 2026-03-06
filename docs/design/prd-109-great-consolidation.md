# Design Decisions: PRD #109 - Great Consolidation

## Overview

This document records the architectural decisions made during the Great Consolidation effort to eliminate "Architectural Schizophrenia" in the Alfred codebase.

## Decision Log

### 1. Storage Unification (M2)

**Decision**: Replace all storage implementations with a single `SQLiteStore` using `sqlite-vec` for vector search.

**Context**:
- Previously: 4 different storage implementations (CAS, SessionStorage, JSONLMemoryStore, FAISSMemoryStore)
- CAS used complex optimistic concurrency with file versioning
- FAISS required 3 files per store (index.faiss, metadata.json, embeddings.npy)
- JSONL had custom serialization logic

**Decision**:
```python
# Before: Multiple stores
CASStore        → cron jobs with versioning
SessionStorage  → custom JSON folders
JSONLMemoryStore → JSONL with embeddings
FAISSMemoryStore → 3-file FAISS format

# After: Single unified store
SQLiteStore     → SQLite + sqlite-vec
```

**Rationale**:
- SQLite provides ACID guarantees without CAS complexity
- sqlite-vec stores vectors + metadata in single table
- Single connection pool, single schema, single backup strategy
- WAL mode provides concurrency without custom locking

**Tradeoffs**:
- ✅ Simpler mental model (one storage API)
- ✅ ACID transactions replace optimistic concurrency
- ✅ Single database file instead of scattered files
- ⚠️ Requires sqlite-vec extension (fallback to numpy if unavailable)

---

### 2. Session Management Consolidation (M2/M5)

**Decision**: Merge `SessionStorage` into `SessionManager`, backed by `SQLiteStore`.

**Context**:
- Originally 5 classes managed session concerns
- `SessionStorage` and `SessionManager` both managed lifecycle
- File I/O scattered across multiple methods

**New Architecture**:
```
Before (5 classes):
├── Session                → In-memory state
├── SessionMeta           → On-disk metadata
├── SessionManager        → Lifecycle + singleton
├── SessionStorage        → File I/O persistence
└── SessionContextBuilder → Prompt assembly

After (3 classes):
├── Session               → In-memory state (unchanged)
├── SessionManager        → Lifecycle + persistence (uses SQLiteStore)
└── SessionContextBuilder → Prompt assembly (unchanged)
```

**Key Changes**:
- `SessionManager` now owns persistence via `SQLiteStore`
- Removed file-based session folders, moved to SQLite table
- Simplified cache management (no TTL cache for metadata)

**Rationale**:
- Separation between SessionStorage and Manager was artificial
- Both managed the same entity lifecycle
- SQLite handles atomicity better than file operations

---

### 3. Search Logic Consolidation (M4)

**Decision**: Move `MemorySearcher` and `ContextBuilder` from `src/search.py` into `src/context.py`, backed by `SQLiteStore`.

**Context**:
- `MemorySearcher` duplicated search logic in `search_memories.py` tool
- `ContextBuilder` was tightly coupled to `MemorySearcher`
- Both had complex hybrid scoring that belonged together

**New Architecture**:
```python
# Before: Separate module
src/search.py
├── MemorySearcher    → Hybrid scoring, deduplication
└── ContextBuilder    → Context assembly

# After: Integrated in context module
src/context.py
├── ContextBuilder
│   ├── search_memories()  → Uses SQLiteStore
│   ├── _hybrid_score()    → Similarity + recency
│   ├── _deduplicate()     → Embedding similarity
│   └── build_context()    → Full context assembly
└── ContextLoader
    └── assemble_with_search() → Uses ContextBuilder
```

**Key Changes**:
- `ContextBuilder` now uses `SQLiteStore.search_memories()` directly
- Hybrid scoring (similarity + recency) moved into builder
- Deduplication logic centralized
- Removed 175 lines of `src/search.py`

**Rationale**:
- Search is a context concern, not a standalone module
- SQLiteStore provides vector search, builder adds scoring
- Single place to adjust hybrid weights and dedup thresholds

---

### 4. Tool Pattern Extraction (M6)

**Decision**: Create shared mixins for common tool patterns, reducing boilerplate by 30%.

**Context**:
- 12 tool classes with similar patterns
- Common: memory store access, error handling, result formatting
- Each tool repeated: `__init__`, `set_memory_store()`, error checks

**Mixin Architecture**:
```python
# src/tools/mixins.py
class MemoryStoreMixin:
    """Memory store access pattern."""
    def __init__(self, memory_store=None): ...
    def set_memory_store(self, store): ...
    def _require_memory_store(self): ...

class ErrorHandlingMixin:
    """Consistent error formatting."""
    async def _handle_error(self, msg, exc): ...
    def _format_success(self, msg, details): ...

class SearchResultMixin:
    """Search result formatting."""
    def _format_entry(self, entry, sim, score): ...
    def _format_results(self, results, sims, scores): ...

class TagParsingMixin:
    """Comma-separated tag parsing."""
    def _parse_tags(self, tags_str): ...
    def _format_tags(self, tags): ...

class ContentTruncationMixin:
    """Content truncation with suffix."""
    def _truncate(self, content, max_len=100): ...
```

**Refactored Tools**:

```python
# Before: RememberTool (~60 lines of boilerplate)
class RememberTool(Tool):
    def __init__(self, memory_store=None):
        super().__init__()
        self._memory_store = memory_store
    
    def set_memory_store(self, store):
        self._memory_store = store
    
    async def execute_stream(self, **kwargs):
        if not self._memory_store:
            yield "Error: Memory store not initialized"
            return
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        truncated = content[:100]
        suffix = "..." if len(content) > 100 else ""

# After: RememberTool (~40 lines, mixins handle boilerplate)
class RememberTool(Tool, MemoryStoreMixin, TagParsingMixin, ContentTruncationMixin):
    def __init__(self, memory_store=None):
        Tool.__init__(self)
        MemoryStoreMixin.__init__(self, memory_store)
    
    async def execute_stream(self, **kwargs):
        if not self._memory_store:  # Still explicit for clarity
            yield "Error: Memory store not initialized"
            return
        tag_list = self._parse_tags(tags)
        truncated = self._truncate(content)
```

**Measured Reduction**:
- `remember.py`: 60 lines → 42 lines (30% reduction)
- `search_memories.py`: 90 lines → 55 lines (39% reduction)

---

### 5. Dead Code Elimination (M1)

**Decision**: Delete unused code without deprecation cycle (per AGENTS.md Rule 3).

**Deleted Files**:
| File | Lines | Reason |
|------|-------|--------|
| `src/interfaces/cli.py` | 645 | Never imported in production |
| `tests/test_cli.py` | 334 | Tests for deleted code |
| `MagicMock/` | ~500 | Orphaned test fixtures |
| `src/utils/cas_store.py` | 415 | Replaced by SQLite |
| `src/memory/faiss_store.py` | 470 | Replaced by SQLite |
| `src/memory/jsonl_store.py` | 370 | Replaced by SQLite |
| `src/session_storage.py` | ~350 | Merged into SessionManager |
| `src/search.py` | 175 | Merged into context.py |

**Total Deleted**: ~3,200 lines

**Rationale**:
- Beta product - no backward compatibility requirement
- Dead code creates confusion and maintenance burden
- Tests for dead code slow CI without adding value

---

### 6. MemoryEntry Dataclass Consolidation

**Decision**: Define `MemoryEntry` in `src/memory/base.py` instead of JSONL-specific module.

**Context**:
- Originally defined in `src/memory/jsonl_store.py`
- ContextBuilder and tools imported from JSONL module
- Created false dependency on JSONL implementation

**Solution**:
```python
# src/memory/base.py
@dataclass
class MemoryEntry:
    """Single memory entry - storage agnostic."""
    entry_id: str
    content: str
    timestamp: datetime
    role: Literal["user", "assistant", "system"] = "assistant"
    embedding: list[float] | None = None
    tags: list[str] = field(default_factory=list)
    permanent: bool = False
```

**Impact**:
- ContextBuilder no longer depends on JSONL store
- MemoryEntry is storage-backend agnostic
- Hashable for deduplication in ContextBuilder

---

### 7. Context Building Best-Effort Approach

**Decision**: Remove hardcoded fallback strings, use best-effort context building.

**Before**:
```python
def _build_system_prompt(self, files):
    if len(files) < 4:
        return "You are Alfred, a helpful AI assistant."  # Hardcoded!
    parts = [...]  # Build from files
```

**After**:
```python
def _build_system_prompt(self, files):
    parts = []
    for name in ["system", "agents", "soul", "user"]:
        if name in files:
            parts.append(f"# {name.upper()}\n\n{files[name].content}")
    return "\n\n---\n\n".join(parts) if parts else ""
```

**Rationale**:
- Hardcoded fallbacks mask configuration issues
- Best-effort shows what's actually available
- Empty string is safer than incorrect persona

---

## Success Metrics

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Zero dead code | grep returns empty | ✅ All deleted files verified | Complete |
| Single storage driver | SQLite only | ✅ SQLiteStore for all data | Complete |
| Delete CAS/JSONL/FAISS | Files removed | ✅ All 3 deleted | Complete |
| Delete search.py | File removed | ✅ Deleted, logic merged | Complete |
| Session 5→3 classes | 3 classes | ✅ 3 classes | Complete |
| Tool boilerplate -30% | 30% reduction | ✅ 30-39% measured | Complete |

**Lines of Code Impact**:
- Deleted: ~3,200 lines
- Added: ~900 lines (SQLiteStore, mixins, tests)
- **Net reduction: ~2,300 lines**

---

## Migration Notes

For existing installations:
1. Old session folders in `data/sessions/` are not migrated
2. Memories from JSONL/FAISS stores are not migrated
3. Beta product - fresh start recommended
4. SQLite database created at `data/alfred.db`

---

## References

- PRD: `prds/109-great-consolidation.md`
- SQLiteStore: `src/storage/sqlite.py`
- Tool Mixins: `src/tools/mixins.py`
- Memory Types: `src/memory/base.py`
