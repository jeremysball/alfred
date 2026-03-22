# Execution Plan: PRD #143 - Milestone 1

## Overview

Lock the cosine-similarity contract with explicit failing tests before changing the storage or caller implementation.

This milestone is intentionally red-first. The goal is to make the current distance/similarity mismatch undeniable and reproducible in versioned tests.

---

## Milestone 1: Lock the contract with failing tests

### Component: Memory search contract

- [ ] **Test**: `test_search_memories_returns_higher_is_better_similarity_contract()`
  - Create `tests/storage/test_sqlite_similarity_semantics.py`
  - Seed two memory vectors where the closer match currently has a lower raw distance
  - Assert Alfred-facing `similarity` ranks the closer match higher
- [ ] **Implement**: add only the fixture/setup helpers needed to express the contract cleanly
  - Do not change production search semantics yet
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_similarity_semantics.py::test_search_memories_returns_higher_is_better_similarity_contract -v` *(expect red)*

### Component: Session summary search contract

- [ ] **Test**: `test_search_summaries_returns_higher_is_better_similarity_contract()`
  - Seed summary vectors with distinct distances
  - Assert the best semantic match exposes the highest Alfred-facing similarity
- [ ] **Implement**: add summary test builders/fixtures only
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_similarity_semantics.py::test_search_summaries_returns_higher_is_better_similarity_contract -v` *(expect red)*

### Component: Session message search contract

- [ ] **Test**: `test_search_session_messages_returns_higher_is_better_similarity_contract()`
  - Seed message embedding rows for one session
  - Assert the closest message yields the highest Alfred-facing similarity
- [ ] **Implement**: add message-index test builders/fixtures only
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_similarity_semantics.py::test_search_session_messages_returns_higher_is_better_similarity_contract -v` *(expect red)*

### Component: Caller semantics stay similarity-based

- [ ] **Test**: `test_context_builder_min_similarity_filters_using_higher_is_better_values()`
  - Add to `tests/test_context_memory_scoring.py`
  - Assert a high-quality match survives `min_similarity` filtering while a weaker match does not
- [ ] **Implement**: add only any fixture cleanup needed to express the intended contract
- [ ] **Run**: `uv run pytest tests/test_context_memory_scoring.py::test_context_builder_min_similarity_filters_using_higher_is_better_values -v` *(expect red until Milestone 3)*

- [ ] **Test**: `test_search_sessions_tool_min_similarity_uses_higher_is_better_values()`
  - Add to `tests/test_search_sessions_integration.py`
  - Assert `SearchSessionsTool` includes the best summary and filters weaker results correctly
- [ ] **Implement**: add only fake-store helpers or fixtures needed for the red test
- [ ] **Run**: `uv run pytest tests/test_search_sessions_integration.py::test_search_sessions_tool_min_similarity_uses_higher_is_better_values -v` *(expect red until Milestone 4)*

---

## Files to Modify

1. `tests/storage/test_sqlite_similarity_semantics.py` - new storage-level contract tests
2. `tests/test_context_memory_scoring.py` - memory caller-threshold contract test
3. `tests/test_search_sessions_integration.py` - session caller-threshold contract test

## Commit Strategy

This milestone is a red-test milestone. Keep commits atomic and explicit:
- `test(storage): codify memory similarity contract`
- `test(storage): codify session summary similarity contract`
- `test(storage): codify session message similarity contract`
- `test(context): codify min_similarity contract`
- `test(search): codify session similarity threshold contract`

Do not mix production fixes into this milestone's initial red commits.