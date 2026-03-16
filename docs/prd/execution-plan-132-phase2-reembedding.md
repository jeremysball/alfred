# Execution Plan: PRD #132 - Phase 2: Re-embedding Orchestrator

## Overview

Implement the re-embedding pipeline that re-creates vec0 tables with correct dimensions and re-embeds all existing data when dimension changes are detected.

---

## Phase 2: Safe Re-embedding Pipeline

### EmbeddingReembedder - Core Orchestrator

- [ ] Test: `test_reembedder_initializes_with_store_and_embedder()`
  - Verify EmbeddingReembedder class accepts store and embedder
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_reembedder_init -v`

- [ ] Implement: `EmbeddingReembedder` class scaffold
  - Create class with `__init__(self, store, embedder)`
  - Store references to SQLiteStore and embedder

- [ ] Test: `test_reembed_all_detects_dimension_mismatch()`
  - Verify reembed_all() detects mismatched dimensions
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_reembed_all_detects -v`

- [ ] Implement: `reembed_all(old_dim, new_dim)` method scaffold
  - Method signature with dimension parameters
  - Returns ReembedResult dataclass (success, message, stats)

### Memory Embeddings Re-embedding

- [ ] Test: `test_reembed_memories_creates_new_table()`
  - Verify new vec0 table created with correct dimension
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_reembed_memories_table -v`

- [ ] Implement: `_reembed_memories()` method
  - Fetch all entries from memories base table
  - Generate new embeddings with current embedder
  - Insert into new memory_embeddings vec0 table
  - Return count of re-embedded entries

- [ ] Test: `test_reembed_memories_preserves_all_content()`
  - Verify all memory content preserved after re-embedding
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_reembed_memories_content -v`

- [ ] Test: `test_reembed_memories_progress_logged()`
  - Verify progress logging (e.g., "Re-embedding memory 50/200")
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_reembed_memories_progress -v`

### Session Summaries Re-embedding

- [ ] Test: `test_reembed_session_summaries()`
  - Verify session summaries re-embedded correctly
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_reembed_summaries -v`

- [ ] Implement: `_reembed_session_summaries()` method
  - Fetch all summaries from session_summaries base table
  - Re-embed summary_text with current embedder
  - Insert into new session_summaries_vec table
  - Return count of re-embedded summaries

### Message Embeddings Re-embedding

- [ ] Test: `test_reembed_message_embeddings()`
  - Verify message embeddings re-embedded correctly
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_reembed_messages -v`

- [ ] Implement: `_reembed_message_embeddings()` method
  - Fetch all messages from message_embeddings base table
  - Re-embed content_snippet with current embedder
  - Insert into new message_embeddings_vec table
  - Return count of re-embedded messages

### Table Swapping (Atomic Operation)

- [ ] Test: `test_atomic_table_swap()`
  - Verify old table dropped and new table renamed atomically
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_table_swap -v`

- [ ] Implement: `_swap_vec0_table()` method
  - Drop old vec0 table
  - Rename new table to replace old one
  - Handle within transaction if possible

### Error Handling and Safety

- [ ] Test: `test_reembed_rollback_on_failure()`
  - Verify rollback if any step fails
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_reembed_rollback -v`

- [ ] Implement: Transaction wrapper in `reembed_all()`
  - Wrap re-embedding in transaction
  - Rollback on any exception
  - Preserve old tables if re-embedding fails

- [ ] Test: `test_reembed_preserves_old_table_on_failure()`
  - Verify old table intact if re-embedding fails mid-way
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_preserve_old -v`

### Integration with SQLiteStore

- [ ] Test: `test_store_calls_reembedder_on_mismatch()`
  - Verify SQLiteStore._init() calls reembedder when mismatch detected
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_store_calls -v`

- [ ] Implement: Integration in `SQLiteStore._check_all_dimensions()`
  - If mismatch detected, instantiate EmbeddingReembedder
  - Call reembedder.reembed_all() with old/new dimensions
  - Log progress and results

- [ ] Test: `test_end_to_end_dimension_change()`
  - Full test: create 768-dim DB, switch to 1536, verify all data re-embedded
  - Run: `uv run pytest tests/storage/test_reembedder.py::test_end_to_end -v`

---

## Files to Modify

1. `src/alfred/storage/sqlite.py`
   - Add `EmbeddingReembedder` class
   - Add `_reembed_memories()`, `_reembed_session_summaries()`, `_reembed_message_embeddings()`
   - Add `_swap_vec0_table()` helper
   - Update `_check_all_dimensions()` to call reembedder

2. `tests/storage/test_reembedder.py` (new file)
   - All re-embedding tests

3. `src/alfred/factories.py`
   - May need updates to wire embedder to store for re-embedding

---

## Commit Strategy

Each checkbox = one atomic commit:

1. `test(storage): add EmbeddingReembedder initialization tests`
2. `feat(storage): implement EmbeddingReembedder class scaffold`
3. `test(storage): add memory re-embedding tests`
4. `feat(storage): implement _reembed_memories() method`
5. `test(storage): add session summaries re-embedding tests`
6. `feat(storage): implement _reembed_session_summaries() method`
7. `test(storage): add message embeddings re-embedding tests`
8. `feat(storage): implement _reembed_message_embeddings() method`
9. `test(storage): add table swap tests`
10. `feat(storage): implement _swap_vec0_table() helper`
11. `test(storage): add error handling tests`
12. `feat(storage): add transaction wrapper and rollback support`
13. `test(storage): add end-to-end re-embedding test`
14. `feat(storage): integrate reembedder into SQLiteStore._init()`

---

## Verification Commands

```bash
# Run all re-embedding tests
uv run pytest tests/storage/test_reembedder.py -v

# Run with coverage
uv run pytest tests/storage/test_reembedder.py --cov=src/alfred/storage/sqlite.py -v

# Full integration test
uv run pytest tests/storage/ -v
```

---

## Success Criteria

- [ ] Can re-embed all memories when dimension changes
- [ ] Can re-embed all session summaries when dimension changes
- [ ] Can re-embed all message embeddings when dimension changes
- [ ] Progress is logged during re-embedding
- [ ] Failed re-embedding preserves old data
- [ ] Table swap is atomic (no partial state)
- [ ] All content preserved during re-embedding
- [ ] End-to-end test passes (create 768 DB → switch to 1536 → verify searchable)

---

## Next Phase Preview

**Phase 3: Integration and Safety**
- Add CLI command `/rebuild-vectors` for manual triggering
- Add --skip-reembed flag for emergency startup
- Add backup before re-embedding option
- Performance optimization for large datasets

Run `/prd-exec 132` after completing Phase 2 to see Phase 3 plan.
