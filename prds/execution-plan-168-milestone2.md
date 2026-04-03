# Execution Plan: PRD #168 - Milestone 2: Add Profile Storage and Effective-Value Retrieval

## Overview
This phase extends the Milestone 1 support-profile contract into durable storage and retrieval. The goal is to persist validated relational and support profile values with timestamps, then resolve effective values across global, context, and arc scopes without yet introducing runtime policy compilation or bounded adaptation.

## Current Repo Constraints
- `src/alfred/memory/support_profile.py` currently defines the validation contract but stops short of persistence helpers and timestamps.
- `src/alfred/storage/sqlite.py` is the single persistence boundary and already owns the support-memory schema for domains, arcs, episodes, and evidence refs.
- Existing support-memory models in `src/alfred/memory/support_memory.py` use explicit `to_record()` / `from_record()` helpers and `created_at` / `updated_at` timestamps. Milestone 2 should match that style instead of inventing a separate persistence convention.
- PRD #168 requires one uniform scope object shape and later milestones will rely on scope precedence, so storage should preserve `scope_type` and `scope_id` exactly rather than collapsing them into ad hoc encodings.
- Milestone 2 should stop at storage and effective-value retrieval. It should not add runtime context inference, behavior compilation, or automatic adaptation logic.

## Success Signal
- Alfred can persist relational and support profile values with timestamps, status, source, confidence, evidence refs, and validated scope.
- SQLite round-trips stored support-profile values without losing schema version, scope identity, or evidence ordering.
- Alfred can resolve the most specific effective value for a registry/dimension pair by preferring arc scope over context scope over global scope.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/test_support_profile.py tests/storage/test_support_profile_storage.py` and `uv run mypy --strict src/`
- **Targeted tests for this phase:** `uv run pytest tests/test_support_profile.py tests/storage/test_support_profile_storage.py -v`

---

## Phase 1: Milestone 2 - Add profile storage and effective-value retrieval

### Persisted support-profile record contract

- [x] Test: `test_support_profile_value_round_trips_through_storage_records()` - verify persisted support-profile values serialize and deserialize with timestamps, scope, confidence, and evidence refs intact.
- [x] Implement: extend the typed support-profile value model with `created_at`, `updated_at`, and explicit `to_record()` / `from_record()` helpers that match the existing support-memory persistence style.
- [x] Run: `uv run pytest tests/test_support_profile.py::test_support_profile_value_round_trips_through_storage_records -v`

### SQLite support-profile storage

- [x] Test: `test_support_profile_values_round_trip_through_sqlite_store()` - verify SQLite stores and reloads multiple support-profile values without losing scope, timestamps, or evidence refs.
- [x] Implement: add the support-profile table, indexes, and `SQLiteStore` save/list/get helpers for persisted support-profile values.
- [x] Run: `uv run pytest tests/storage/test_support_profile_storage.py::test_support_profile_values_round_trip_through_sqlite_store -v`

### Effective-value resolution by scope

- [ ] Test: `test_sqlite_store_resolves_most_specific_support_profile_value()` - verify Alfred resolves arc-scoped values first, then context-scoped values, then global values for the same registry/dimension.
- [ ] Implement: add the minimal retrieval helper that applies scope precedence for one registry/dimension query without pulling in later behavior-compiler logic.
- [ ] Run: `uv run pytest tests/storage/test_support_profile_storage.py::test_sqlite_store_resolves_most_specific_support_profile_value -v`

---

## Files to Modify

1. `src/alfred/memory/support_profile.py` - add persisted value timestamps and record helpers
2. `src/alfred/memory/__init__.py` - re-export any new support-profile helpers needed by callers
3. `src/alfred/storage/sqlite.py` - add support-profile table creation and retrieval methods
4. `tests/test_support_profile.py` - record-contract tests for persisted support-profile values
5. `tests/storage/test_support_profile_storage.py` - SQLite round-trip and scope-precedence tests

## Commit Strategy

Each completed test → implement → run block should map cleanly to one atomic commit:
- `feat(memory): add persisted support profile value record`
- `feat(storage): store support profile values in sqlite`
- `feat(storage): resolve support profile values by scope`
