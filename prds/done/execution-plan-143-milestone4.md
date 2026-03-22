# Execution Plan: PRD #143 - Milestone 4

## Overview

Apply the same corrected semantics to session retrieval so session summaries and in-session message hits expose the same higher-is-better similarity contract as memory search.

---

## Milestone 4: Migrate session search to the new contract

### Component: Summary search normalization

- [ ] **Test**: `test_search_summaries_normalizes_backend_distance_to_alfred_similarity()`
  - Use the red contract test from Milestone 1 as the acceptance test
- [ ] **Implement**: update `SQLiteStore.search_summaries()` in `src/alfred/storage/sqlite.py`
  - Return Alfred-facing similarity instead of raw distance
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_similarity_semantics.py::test_search_summaries_normalizes_backend_distance_to_alfred_similarity -v`

### Component: Session-message search normalization

- [ ] **Test**: `test_search_session_messages_normalizes_backend_distance_to_alfred_similarity()`
  - Assert the best message hit returns the highest similarity value
- [ ] **Implement**: update `SQLiteStore.search_session_messages()` in `src/alfred/storage/sqlite.py`
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_similarity_semantics.py::test_search_session_messages_normalizes_backend_distance_to_alfred_similarity -v`

### Component: SearchSessionsTool threshold behavior

- [ ] **Test**: `test_search_sessions_tool_filters_summaries_using_normalized_similarity()`
  - Add to `tests/test_search_sessions_integration.py`
  - Assert a semantically relevant summary appears when it exceeds `min_similarity`
- [ ] **Implement**: update `src/alfred/tools/search_sessions.py` only if caller logic still assumes raw backend distance
- [ ] **Run**: `uv run pytest tests/test_search_sessions_integration.py::test_search_sessions_tool_filters_summaries_using_normalized_similarity -v`

### Component: User-facing relevance output

- [ ] **Test**: `test_search_sessions_tool_reports_relevance_from_normalized_similarity()`
  - Assert rendered output shows the corrected higher-is-better value
- [ ] **Implement**: keep formatting in `src/alfred/tools/search_sessions.py` aligned with the new storage contract
- [ ] **Run**: `uv run pytest tests/test_search_sessions_integration.py::test_search_sessions_tool_reports_relevance_from_normalized_similarity -v`

---

## Files to Modify

1. `src/alfred/storage/sqlite.py` - session summary and message normalization
2. `src/alfred/tools/search_sessions.py` - thresholding and relevance output
3. `tests/storage/test_sqlite_similarity_semantics.py` - session storage semantics checks
4. `tests/test_search_sessions_integration.py` - tool-level behavior checks

## Commit Strategy

Suggested atomic commits:
- `fix(storage): normalize session summary similarity`
- `fix(storage): normalize session message similarity`
- `fix(search): honor normalized summary thresholds`
- `test(search): verify normalized session relevance output`