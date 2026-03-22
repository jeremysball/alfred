# Execution Plan: PRD #143 - Milestone 3

## Overview

Migrate the memory retrieval path onto the new contract so Alfred memory callers see real higher-is-better similarity values.

---

## Milestone 3: Migrate memory search to the new contract

### Component: Storage-layer normalization

- [ ] **Test**: `test_search_memories_normalizes_backend_distance_to_alfred_similarity()`
  - Use the red test from Milestone 1 or refine it if needed
  - Assert the returned field is Alfred-facing similarity, not raw distance
- [ ] **Implement**: update `SQLiteStore.search_memories()` in `src/alfred/storage/sqlite.py`
  - Keep raw distance internal
  - Return normalized `similarity` that is higher for better matches
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_similarity_semantics.py::test_search_memories_normalizes_backend_distance_to_alfred_similarity -v`

### Component: Memory-store wrapper preservation

- [ ] **Test**: `test_sqlite_memory_store_forwards_normalized_similarity_scores()`
  - Add to `tests/test_memory_integration.py`
  - Assert `SQLiteMemoryStore.search()` preserves normalized similarity values from the store
- [ ] **Implement**: update `src/alfred/memory/sqlite_store.py` only if needed to keep the corrected contract intact end to end
- [ ] **Run**: `uv run pytest tests/test_memory_integration.py::test_sqlite_memory_store_forwards_normalized_similarity_scores -v`

### Component: ContextBuilder threshold behavior

- [ ] **Test**: `test_context_builder_min_similarity_accepts_best_memory_match_after_normalization()`
  - Add or adapt in `tests/test_context_memory_scoring.py`
  - Assert the best match survives thresholding when it should
- [ ] **Implement**: update `src/alfred/context.py` only if caller logic still leaks backend assumptions
- [ ] **Run**: `uv run pytest tests/test_context_memory_scoring.py::test_context_builder_min_similarity_accepts_best_memory_match_after_normalization -v`

### Component: Hybrid ranking behavior

- [ ] **Test**: `test_context_builder_hybrid_score_ranks_higher_similarity_above_lower_similarity_when_recency_is_equal()`
  - Assert corrected similarity semantics drive expected ranking
- [ ] **Implement**: verify or adjust `_hybrid_score()` integration in `src/alfred/context.py` without changing its intended weighting model
- [ ] **Run**: `uv run pytest tests/test_context_memory_scoring.py::test_context_builder_hybrid_score_ranks_higher_similarity_above_lower_similarity_when_recency_is_equal -v`

---

## Files to Modify

1. `src/alfred/storage/sqlite.py` - memory search normalization
2. `src/alfred/memory/sqlite_store.py` - memory wrapper contract preservation
3. `src/alfred/context.py` - caller behavior on normalized similarity
4. `tests/storage/test_sqlite_similarity_semantics.py` - storage normalization checks
5. `tests/test_memory_integration.py` - memory-store integration checks
6. `tests/test_context_memory_scoring.py` - threshold and ranking checks

## Commit Strategy

Suggested atomic commits:
- `fix(storage): normalize memory search similarity`
- `test(memory): verify sqlite memory store similarity contract`
- `fix(context): honor normalized memory similarity thresholds`
- `test(context): verify hybrid memory ranking with normalized similarity`