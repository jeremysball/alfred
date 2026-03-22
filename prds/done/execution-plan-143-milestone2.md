# Execution Plan: PRD #143 - Milestone 2

## Overview

Teach the SQLite vector layer that schema correctness means more than embedding dimension. Vec tables must carry an explicit cosine metric contract, and drift must be detectable.

---

## Milestone 2: Add vec schema metric awareness

### Component: Vec schema inspection

- [ ] **Test**: `test_get_vec0_metric_returns_none_for_missing_table()`
  - Add to `tests/storage/test_sqlite_vec.py`
  - Verify metric inspection handles a missing vec table cleanly
- [ ] **Implement**: add `_get_vec0_metric()` to `src/alfred/storage/sqlite.py`
  - Read vec table DDL/metadata and extract the configured metric if present
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_vec.py::test_get_vec0_metric_returns_none_for_missing_table -v`

- [ ] **Test**: `test_get_vec0_metric_detects_cosine_table_configuration()`
  - Verify metric inspection recognizes a cosine-configured vec table
- [ ] **Implement**: finalize metric parsing/inspection for created vec tables
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_vec.py::test_get_vec0_metric_detects_cosine_table_configuration -v`

### Component: Drift detection

- [ ] **Test**: `test_vec_schema_validation_detects_metric_drift_with_matching_dimension()`
  - Create a vec table with the expected dimension but the wrong metric
  - Assert the store flags it as drifted
- [ ] **Implement**: extend schema validation so metric drift is treated as a rebuild-triggering mismatch
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_vec.py::test_vec_schema_validation_detects_metric_drift_with_matching_dimension -v`

### Component: Centralized vec table creation

- [ ] **Test**: `test_all_vec_tables_are_created_with_cosine_metric_contract()`
  - Verify `memory_embeddings`, `session_summaries_vec`, and `message_embeddings_vec` are created through one cosine-aware path
- [ ] **Implement**: centralize vec table creation in `src/alfred/storage/sqlite.py`
  - Replace ad hoc creation with one helper that accepts table name and id column
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_vec.py::test_all_vec_tables_are_created_with_cosine_metric_contract -v`

### Component: Initialization guardrail

- [ ] **Test**: `test_store_init_rejects_metric_mismatch_when_rebuild_is_unavailable()`
  - Assert the store fails clearly if it detects metric drift it cannot repair
- [ ] **Implement**: add clear failure behavior for unrecoverable metric drift
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_vec.py::test_store_init_rejects_metric_mismatch_when_rebuild_is_unavailable -v`

---

## Files to Modify

1. `src/alfred/storage/sqlite.py` - vec metric inspection, validation, and creation helper
2. `tests/storage/test_sqlite_vec.py` - metric contract and drift tests

## Commit Strategy

Suggested atomic commits:
- `test(storage): add vec metric inspection coverage`
- `feat(storage): detect vec metric drift`
- `refactor(storage): centralize cosine vec table creation`
- `fix(storage): fail fast on unrecoverable metric drift`