# Execution Plan: PRD #148 - Milestone 2: Base Snapshot Capture

## Overview
Persist the last clean template version so Alfred can reconstruct a merge base after restart. This phase adds base snapshot payloads to the sync store, captures them when a template is created or cleanly updated, and exposes a recovery helper for later merge work.

---

## Milestone 2: Capture base snapshots for synced templates

### Component: Base snapshot payload contract

- [x] **Test**: `test_template_sync_record_round_trips_base_snapshot_payload()` - verify a sync record stores the base snapshot content, hash, and timestamp and survives JSON serialization
- [x] **Implement**: add a `TemplateBaseSnapshot` payload to `TemplateSyncRecord` and serialize it through `TemplateSyncStore`
- [x] **Run**: `uv run pytest tests/test_template_sync.py::test_template_sync_record_round_trips_base_snapshot_payload -v`

### Component: Snapshot capture on first creation

- [x] **Test**: `test_create_new_file_records_base_snapshot_in_cache()` - verify a new template copied into the workspace also writes its initial base snapshot
- [x] **Implement**: capture the initial template content after `create_from_template()` / `ensure_exists()` writes a new file
- [x] **Run**: `uv run pytest tests/test_templates.py::TestCreateFromTemplate::test_create_new_file_records_base_snapshot_in_cache -v`

### Component: Snapshot refresh on clean update

- [x] **Test**: `test_template_manager_refreshes_base_snapshot_after_clean_update()` - verify a successful `update_templates()` call overwrites the stored base snapshot with the latest synced content
- [x] **Implement**: add a snapshot-capture helper in `TemplateManager` and call it from the clean write path
- [x] **Run**: `uv run pytest tests/test_templates.py::TestCreateFromTemplate::test_template_manager_refreshes_base_snapshot_after_clean_update -v`

### Component: Snapshot recovery after restart

- [x] **Test**: `test_template_manager_recovers_base_snapshot_after_restart()` - verify a fresh `TemplateManager` can load the last synced version for a template
- [x] **Implement**: keep the sync store lazy-loaded and expose `TemplateManager.get_base_snapshot()` to recover the saved snapshot by template name
- [x] **Run**: `uv run pytest tests/test_templates.py::TestCreateFromTemplate::test_template_manager_recovers_base_snapshot_after_restart -v`

---

## Files to Modify

1. `src/alfred/template_sync.py` — add base snapshot payload support and persistence helpers
2. `src/alfred/templates.py` — capture and recover snapshots during template sync
3. `tests/test_template_sync.py` — record/store round-trip coverage
4. `tests/test_templates.py` — manager integration coverage

## Commit Strategy

Each completed checkbox should be one atomic commit:
- `test(templates): add base snapshot payload contract`
- `feat(templates): persist initial base snapshots`
- `feat(templates): refresh base snapshots on clean sync`
- `feat(templates): recover base snapshots on manager startup`
- `test(templates): verify base snapshot restart recovery`

## Progress Summary

Milestone 2 is complete.
Continue with Milestone 3: Implement git-style auto-merge on restart in `prds/148-template-sync-merge-conflicts.md`.

## Exit Criteria for Milestone 2

- Alfred can recover the last synced version for each managed template
- Base snapshots survive restarts in durable storage
- Clean syncs refresh the stored base snapshot
- Milestone 3 can use the recovered snapshot for a real 3-way merge
