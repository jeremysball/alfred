# PRD: Great Consolidation - Cleanup Architectural Cruft

**GitHub Issue**: #109  
**Priority**: High  
**Status**: Draft  

## Problem Statement

Alfred has grown through rapid iterations and feature additions. The codebase now exhibits "Architectural Schizophrenia"—multiple patterns for the same concept, dead code that is never imported but maintained, and over-engineered abstractions that no longer serve their purpose.

### Specific Pain Points

1. **Dead Code**: `src/interfaces/cli.py` (645 lines) is never imported in production but has 334 lines of tests
2. **Storage Fragmentation**: Four different storage implementations (CAS, SessionStorage, JSONLMemoryStore, FAISSMemoryStore) for essentially "write JSON to disk"
3. **Interface Drift**: FAISSMemoryStore is incomplete—`alfred memory prune` literally prints "not yet implemented"
4. **Search Duplication**: `MemorySearcher` in `search.py` and inline scoring in `search_memories.py` do the same job
5. **Session Sprawl**: Five classes manage what is essentially "a list of messages with an ID"
6. **Tool Bloat**: Each tool is a separate class inheriting from `Tool` base, but most just wrap single functions
7. **Orphaned Files**: `MagicMock/` directory (42 subdirectories of test fixtures), `dog-fooding-notes.txt`
8. **TODOs**: 5 explicit TODOs in core files including `alfred.py` itself

## Solution Overview

A systematic consolidation effort to:
1. **Delete dead code** and its tests
2. **Consolidate storage** into a unified interface
3. **Complete FAISS implementation** (prune, update, batch operations)
4. **Merge search logic** into a single, reusable component
5. **Simplify session management** to three cohesive classes
6. **Extract shared patterns** from tools into mixins
7. **Clean up** orphaned files and TODOs

## Success Criteria

- [ ] Zero dead code in production (verified via import analysis)
- [ ] Single storage driver per backend type (JSONL, FAISS)
- [ ] All memory CLI commands work for both backends
- [ ] `search.py` removed, logic merged into stores
- [ ] Session classes consolidated from 5 → 3
- [ ] Tool boilerplate reduced by 30% via shared mixins
- [ ] CI passes with stricter dead code detection

## Milestones

### M1: Delete Dead Code (Remove, Don't Preserve)

**Goal**: Eliminate truly unused code without deprecation cycle.

**Changes**:
- Delete `src/interfaces/cli.py` (645 lines)
- Delete `tests/test_cli.py` (334 lines)
- Delete `MagicMock/` directory and contents
- Delete `dog-fooding-notes.txt` (or move to docs/)
- Verify no other files import from deleted modules

**Success Criteria**:
- `grep -r "from src.interfaces.cli import" src/` returns empty
- `ls MagicMock/` returns "No such file or directory"
- CI passes without these files

**Rationale**: Per AGENTS.md Rule 3: "Prefer clean deletion over preservation." These files have been dead for months.

---

### M2: Unify Storage Drivers (DRY Principle)

**Goal**: Collapse four storage implementations into two coherent drivers.

**Current State**:
```
Storage Implementations:
├── CASStore (cron only, complex versioning)
├── SessionStorage (sessions, custom JSON)
├── JSONLMemoryStore (memories, with embeddings)
└── FAISSMemoryStore (memories, incomplete)
```

**Target State**:
```
Storage Drivers:
├── JSONLStore (append-only log, used by: sessions, cron, memories)
└── FAISSStore (vector index, used by: memories)
```

**Implementation**:
1. Create `src/storage/jsonl.py` with unified JSONL driver
   - Supports: append, read_all, filter_by, atomic write
   - Used by: SessionStorage, CronStore, JSONLMemoryStore (migrated)
2. Complete `src/storage/faiss.py` (extracted from current FAISSMemoryStore)
   - Add: `prune_expired()`, `update_entry()`, `add_entries()` (batch)
   - Implement missing interface methods
3. Migrate existing stores to use unified drivers
4. Delete old implementations once migrated

**Success Criteria**:
- All storage operations use one of two drivers
- `src/utils/cas_store.py` deleted
- `src/memory/jsonl_store.py` deleted (functionality moved)
- `src/session_storage.py` uses `JSONLStore` internally
- `src/cron/store.py` uses `JSONLStore` internally

**Risk**: Migration must preserve user data. Test with existing data files.

---

### M3: Complete FAISS Implementation (Fix Broken Features)

**Goal**: Make FAISS store feature-complete.

**Current Gaps**:
- `prune_expired_memories()` → not implemented
- `update_entry()` → not implemented  
- `add_entries()` (batch) → missing
- `check_memory_threshold()` → missing

**Implementation**:
1. Implement `FAISSStore.prune_expired(ttl_days, dry_run)`
   - Load metadata, filter by timestamp, rebuild index
   - Support dry-run mode
2. Implement `FAISSStore.update_entry(entry_id, new_content)`
   - Delete old embedding, add new, update metadata
3. Implement `FAISSStore.add_entries(entries)` (batch)
   - Single index rebuild for N entries vs N rebuilds
4. Implement `FAISSStore.check_memory_threshold(threshold)`
   - Return (over_threshold, current_count)
5. Update `alfred memory prune` to actually work
   - Remove "not yet implemented" message
   - Call `memory_store.prune_expired()`

**Success Criteria**:
- `alfred memory prune --dry-run` shows memories that would be deleted
- `alfred memory prune` actually deletes expired memories
- Feature parity between JSONL and FAISS backends

---

### M4: Consolidate Search Logic (Remove Duplication)

**Goal**: Merge `search.py` into stores, eliminate duplication.

**Current State**:
- `src/search.py` (175 lines): `MemorySearcher` class with hybrid scoring
- `src/tools/search_memories.py` (160 lines): Inline scoring, similar logic

**Target State**:
- Delete `src/search.py`
- Move hybrid scoring into `FAISSStore.search()` and `JSONLStore.search()`
- `ContextBuilder` uses store methods directly

**Implementation**:
1. Add `hybrid_search()` method to both stores
   - Semantic similarity + recency scoring
   - Configurable weights
2. Update `ContextBuilder` to call `store.hybrid_search()`
3. Update `SearchMemoriesTool` to call `memory_store.hybrid_search()`
4. Delete `src/search.py`

**Success Criteria**:
- `src/search.py` deleted
- `grep -r "from src.search import" src/` returns empty
- Hybrid scoring works for both stores
- Context building uses unified interface

---

### M5: Simplify Session Management (5 → 3 Classes)

**Goal**: Reduce session sprawl while maintaining separation of concerns.

**Current State (5 classes)**:
- `Session`: In-memory state
- `SessionMeta`: On-disk metadata
- `SessionManager`: Lifecycle + singleton
- `SessionStorage`: Persistence
- `SessionContextBuilder`: Prompt assembly

**Target State (3 classes)**:
- `Session`: In-memory state (unchanged)
- `SessionManager`: Lifecycle + persistence (merges Manager + Storage)
- `SessionContextBuilder`: Prompt assembly (unchanged)

**Implementation**:
1. Merge `SessionStorage` into `SessionManager`
   - `SessionManager` uses `JSONLStore` internally
   - Move `get_cli_current()`, `set_cli_current()`, persistence methods
2. Delete `SessionStorage` class
3. Keep `SessionContextBuilder` separate (different responsibility)

**Success Criteria**:
- `src/session_storage.py` deleted
- `SessionManager` has all persistence methods
- No functionality lost
- Tests updated

---

### M6: Extract Tool Patterns (Reduce Boilerplate)

**Goal**: Reduce tool boilerplate by 30% via shared mixins.

**Current State**:
- 12 tool classes, each 100-200 lines
- Common patterns: error handling, result formatting, pagination
- Each tool repeats similar boilerplate

**Target State**:
- `ToolBase`: Existing base class
- `MemoryToolMixin`: For tools that need memory store access
- `SearchResultMixin`: For formatting search results
- `ErrorHandlingMixin`: For consistent error patterns

**Implementation**:
1. Create `src/tools/mixins.py`
   - `MemoryToolMixin`: `_get_memory_store()`, `_require_store()`
   - `SearchResultMixin`: `_format_results()`, `_format_entry()`
   - `ErrorHandlingMixin`: `_handle_error()`, `_yield_error()`
2. Refactor 3-4 representative tools to use mixins
3. Verify boilerplate reduction (target: 30% fewer lines)
4. Document pattern for future tools

**Success Criteria**:
- `src/tools/mixins.py` created
- At least 4 tools refactored
- Average tool file size reduced by 30%
- No functionality lost

---

### M7: Clean Up TODOs and Orphaned Code

**Goal**: Address 5 TODOs and remove orphaned patterns.

**TODOs to Address**:
1. `src/alfred.py`: "# TODO: Implement in M9" (compaction)
2. `src/tools/schedule_job.py`: "# TODO: Implement the job logic"
3. `src/cron/system_jobs.py`: "# TODO: Query session store"
4. `src/session_storage.py`: "# TODO: Add proper logging"
5. `src/cli/cron.py`: "# TODO: Implement job logic"

**Implementation**:
1. For each TODO:
   - If truly needed: Implement it
   - If obsolete: Delete the TODO comment
   - If future work: Create GitHub issue, reference in comment
2. Remove `@async_command` decorator from `cron.py` (dead code after M1 fixes)
3. Clean up any remaining orphaned imports

**Success Criteria**:
- `grep -r "TODO\|FIXME" src/ | wc -l` ≤ 2 (only legitimate future work)
- No orphaned imports
- All TODOs either implemented, deleted, or converted to issues

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| TBD | Delete cli.py without deprecation | Per AGENTS.md Rule 3: "Prefer clean deletion over preservation." File is dead code. |
| TBD | Merge SessionStorage into SessionManager | Both manage session lifecycle; separation adds indirection without benefit. |
| TBD | Keep SessionContextBuilder separate | Different responsibility (prompt assembly vs. lifecycle management). |
| TBD | Complete FAISS before deleting JSONL | User data preservation is critical. Migration path must be tested. |

## Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during storage migration | High | Test with existing data files before migration. Keep backups. |
| Breaking external integrations | Medium | Verify no external packages import from deleted modules. |
| Tool refactor breaks LLM tool calling | High | Test each refactored tool with actual LLM calls. |
| FAISS completion is complex | Medium | Break into smaller PRs (prune first, then update, then batch). |

## Testing Strategy

1. **Dead Code Removal**: Verify via `grep` that deleted modules aren't imported
2. **Storage Migration**: Test with existing user data files (backup first)
3. **FAISS Completion**: Unit tests for each new method + integration test
4. **Tool Refactor**: Test each tool with mocked LLM calls
5. **Regression**: Full `pytest` suite must pass after each milestone

## Implementation Order

Recommended order (dependencies considered):
1. **M1**: Delete dead code (no dependencies, reduces noise)
2. **M7**: Clean up TODOs (no dependencies, quick wins)
3. **M2**: Unify storage (foundational for M3, M4, M5)
4. **M3**: Complete FAISS (depends on M2 storage interface)
5. **M4**: Consolidate search (depends on M2, M3)
6. **M5**: Simplify sessions (depends on M2)
7. **M6**: Extract tool patterns (independent, can be done in parallel)

## Notes

- This is internal refactoring. No user-facing changes.
- Follow AGENTS.md rules: commit early/often, conventional commits, test first.
- Each milestone should be independently committable.
- Use `git rm` for deletions, not just `rm` (preserve git history).
