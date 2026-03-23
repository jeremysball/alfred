# Execution Plan: PRD #148 - Milestone 1: Sync Metadata Contract

## Overview
Define and persist the metadata Alfred needs to reason about template drift: base snapshot, current workspace state, template hash, and conflict status. This phase only establishes the contract and durable storage surface; the merge algorithm and WebUI warning come later.

---

## Milestone 1: Define the sync metadata contract

### Component: Sync record schema

- [x] **Test**: `test_template_sync_record_captures_template_workspace_and_base_hashes()` - verify a sync record stores template hash, workspace hash, base hash, and per-file status
- [x] **Implement**: add `src/alfred/template_sync.py` with a structured sync record model and explicit state enum
- [x] **Run**: `uv run pytest tests/test_template_sync.py::test_template_sync_record_captures_template_workspace_and_base_hashes -v`

### Component: Sync store round-trip

- [x] **Test**: `test_template_sync_store_round_trips_records()` - verify records can be saved, loaded, and survive a restart without losing base snapshot data
- [x] **Implement**: add a small JSON-backed sync store with atomic writes and load-on-start behavior
- [x] **Run**: `uv run pytest tests/test_template_sync.py::test_template_sync_store_round_trips_records -v`

### Component: State classification helpers

- [x] **Test**: `test_template_sync_state_distinguishes_clean_merged_and_conflicted_records()` - verify helper methods classify clean, merged, pending, and conflicted states consistently
- [x] **Implement**: add helper methods for `is_clean()`, `needs_merge()`, and `is_conflicted()` so later phases can branch cleanly
- [x] **Run**: `uv run pytest tests/test_template_sync.py::test_template_sync_state_distinguishes_clean_merged_and_conflicted_records -v`

---

## Files to Modify

1. `src/alfred/template_sync.py` — new sync-state model and store helpers
2. `src/alfred/templates.py` — integrate the sync contract into template management, if needed
3. `tests/test_template_sync.py` — new contract tests for sync records and persistence

## Commit Strategy

Each completed checkbox should be one atomic commit:
- `test(templates): define template sync record contract`
- `feat(templates): add sync store persistence`
- `test(templates): verify sync state classification`

## Exit Criteria for Milestone 1

- Alfred has a durable, queryable template sync contract
- Base snapshots can survive restarts
- Later merge and conflict logic can build on a stable state model
- Milestone 2 can implement 3-way merge behavior without rethinking storage shape
