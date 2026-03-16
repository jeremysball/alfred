# Execution Plan: PRD #132 - Phase 1: Dimension Detection

## Overview

Implement automatic detection of embedding dimension mismatches between the configured embedder and existing sqlite-vec tables. This is the foundation for the re-embedding pipeline.

---

## Phase 1: Dimension Detection and Comparison

### SQLiteStore - Schema Introspection

- [ ] Test: `test_get_vec0_dimension_returns_none_for_missing_table()`
  - Verify `_get_vec0_dimension()` returns None when table doesn't exist
  - Run: `uv run pytest tests/storage/test_sqlite_vec.py::test_get_vec0_dimension_returns_none -v`

- [ ] Test: `test_get_vec0_dimension_extracts_float768()`
  - Create vec0 table with FLOAT[768], verify extraction returns 768
  - Run: `uv run pytest tests/storage/test_sqlite_vec.py::test_get_vec0_dimension_extracts -v`

- [ ] Implement: `_get_vec0_dimension(db, table_name)` method
  - Query `sqlite_master` for table schema
  - Use regex to extract FLOAT[N] dimension
  - Return int dimension or None

- [ ] Test: `test_get_vec0_dimension_extracts_float1536()`
  - Verify works with different dimensions (1536)
  - Run: `uv run pytest tests/storage/test_sqlite_vec.py::test_get_vec0_dimension_1536 -v`

### SQLiteStore - Dimension Comparison

- [ ] Test: `test_check_dimension_match_when_equal()`
  - Create table with 768, embedder.dimension=768, verify no mismatch
  - Run: `uv run pytest tests/storage/test_sqlite_vec.py::test_check_dimension_match -v`

- [ ] Test: `test_check_dimension_mismatch_when_different()`
  - Create table with 768, embedder.dimension=1536, verify mismatch detected
  - Run: `uv run pytest tests/storage/test_sqlite_vec.py::test_check_dimension_mismatch -v`

- [ ] Implement: `_check_dimension_mismatch()` method
  - Get actual dimension from vec0 table
  - Compare with `self._embedding_dim`
  - Return `(old_dim, new_dim)` tuple or None

- [ ] Test: `test_check_dimension_returns_none_for_new_table()`
  - Verify no mismatch when table doesn't exist (will be created)
  - Run: `uv run pytest tests/storage/test_sqlite_vec.py::test_check_new_table -v`

### SQLiteStore - Integration

- [ ] Test: `test_init_detects_dimension_on_startup()`
  - Create store with mismatched dimension, verify detection logged
  - Run: `uv run pytest tests/storage/test_sqlite_vec.py::test_init_detects -v`

- [ ] Implement: Dimension check in `_init()`
  - Call `_check_dimension_mismatch()` during initialization
  - Log warning if mismatch detected: "Dimension changed X -> Y"
  - Store mismatch info for later re-embedding

- [ ] Test: `test_dimension_check_skipped_when_match()`
  - Verify no warning logged when dimensions match
  - Run: `uv run pytest tests/storage/test_sqlite_vec.py::test_no_warning_on_match -v`

### SQLiteStore - All Three Tables

- [ ] Test: `test_checks_all_vec0_tables()`
  - Verify dimension check runs for all three tables (memory_embeddings, message_embeddings_vec, session_summaries_vec)
  - Run: `uv run pytest tests/storage/test_sqlite_vec.py::test_checks_all_tables -v`

- [ ] Implement: Loop through all vec0 tables in `_init()`
  - Check each table's dimension
  - Report which tables need re-embedding

---

## Files to Modify

1. `src/alfred/storage/sqlite.py`
   - Add `_get_vec0_dimension()` method
   - Add `_check_dimension_mismatch()` method  
   - Update `__init__()` to accept `embedding_dim` parameter
   - Update `_init()` to check dimensions on startup
   - Update `_create_message_embeddings_table()` and `_create_memories_table()` to use dynamic dimension

2. `tests/storage/test_sqlite_vec.py` (new file)
   - All dimension detection tests

3. `src/alfred/factories.py`
   - Update `SQLiteStoreFactory.create()` to pass embedder dimension

4. `src/alfred/core.py`
   - Ensure embedder is created before SQLiteStore so dimension is available

---

## Commit Strategy

Each checkbox = one atomic commit:

1. `test(storage): add tests for vec0 dimension extraction`
2. `feat(storage): implement _get_vec0_dimension() method`
3. `test(storage): add tests for dimension mismatch detection`
4. `feat(storage): implement _check_dimension_mismatch() method`
5. `feat(storage): integrate dimension check into _init()`
6. `test(storage): verify all vec0 tables are checked`
7. `feat(storage): check all three vec0 tables for dimension mismatch`
8. `refactor(factories): pass embedding_dim to SQLiteStore`
9. `refactor(core): initialize embedder before SQLiteStore`

---

## Verification Commands

```bash
# Run all new tests
uv run pytest tests/storage/test_sqlite_vec.py -v

# Run with coverage
uv run pytest tests/storage/test_sqlite_vec.py --cov=src/alfred/storage/sqlite.py -v

# Verify no regressions
uv run pytest tests/ -k sqlite --tb=short
```

---

## Success Criteria

- [ ] Can detect dimension mismatch between existing table (768) and new embedder (1536)
- [ ] Can detect when table doesn't exist (return None, no error)
- [ ] Logs warning with old_dim -> new_dim when mismatch detected
- [ ] All three vec0 tables checked: memory_embeddings, message_embeddings_vec, session_summaries_vec
- [ ] No false positives when dimensions match
- [ ] Tests cover edge cases (missing table, different dims, matching dims)

---

## Next Phase Preview

**Phase 2: Re-embedding Orchestrator**
- Create `EmbeddingReembedder` class
- Implement `reembed_all()` orchestration method
- Add progress logging
- Handle failures gracefully

Run `/prd-exec 132` after completing Phase 1 to see Phase 2 plan.
