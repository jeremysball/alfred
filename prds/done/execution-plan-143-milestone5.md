# Execution Plan: PRD #143 - Milestone 5

## Overview

Add a safe rebuild path so existing vec indexes can move to the cosine metric contract without leaving Alfred in a partially migrated state.

---

## Milestone 5: Add safe rebuild and startup validation

### Component: Rebuild orchestration entry point

- [ ] **Test**: `test_rebuild_vector_indexes_recreates_all_metric_drifted_vec_tables()`
  - Add to `tests/storage/test_sqlite_vec.py`
  - Create a store with drifted vec tables and assert the rebuild touches all affected tables
- [ ] **Implement**: add a rebuild orchestration helper in `src/alfred/storage/sqlite.py`
  - Recreate `memory_embeddings`, `session_summaries_vec`, and `message_embeddings_vec` with the cosine contract
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_vec.py::test_rebuild_vector_indexes_recreates_all_metric_drifted_vec_tables -v`

### Component: Memory vec repopulation

- [ ] **Test**: `test_rebuild_vector_indexes_repopulates_memory_embeddings()`
  - Assert rebuilt memory vec rows are searchable after migration
- [ ] **Implement**: repopulate memory vectors from the safest available canonical source during rebuild
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_vec.py::test_rebuild_vector_indexes_repopulates_memory_embeddings -v`

### Component: Session vec repopulation

- [ ] **Test**: `test_rebuild_vector_indexes_repopulates_session_summary_and_message_vec_tables()`
  - Assert rebuilt summary/message vec rows are searchable after migration
- [ ] **Implement**: repopulate `session_summaries_vec` and `message_embeddings_vec` from canonical sources already stored by Alfred
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_vec.py::test_rebuild_vector_indexes_repopulates_session_summary_and_message_vec_tables -v`

### Component: Startup validation behavior

- [ ] **Test**: `test_store_initialization_triggers_or_demands_rebuild_on_metric_drift()`
  - Assert initialization either repairs drift safely or fails with a clear error when repair is unavailable
- [ ] **Implement**: wire metric validation into initialization/startup flow in `src/alfred/storage/sqlite.py`
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_vec.py::test_store_initialization_triggers_or_demands_rebuild_on_metric_drift -v`

---

## Files to Modify

1. `src/alfred/storage/sqlite.py` - rebuild helper and startup validation
2. `tests/storage/test_sqlite_vec.py` - rebuild and startup tests

## Commit Strategy

Suggested atomic commits:
- `feat(storage): add vec rebuild orchestration`
- `fix(storage): repopulate rebuilt memory vectors`
- `fix(storage): repopulate rebuilt session vectors`
- `fix(storage): validate metric drift at startup`