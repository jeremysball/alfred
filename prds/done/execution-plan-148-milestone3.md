# Execution Plan: PRD #148 - Milestone 3: Git-Style Auto-Merge on Restart

## Overview
Use the saved merge base to fast-forward clean template drift before any context is read. This phase only covers successful restart-safe merges and snapshot refreshes; conflict-marker output is Milestone 4.

---

## Phase 3: Clean restart merge

### Component: Fast-forward clean restart state

- [x] **Test**: `test_update_templates_ignores_mtime_when_workspace_matches_saved_base()` - verify a template newer than the workspace still gets applied when the workspace content matches the saved base snapshot.
- [x] **Implement**: add a per-template reconciliation helper in `TemplateManager` that compares template/workspace/base content, fast-forwards clean cases, refreshes the sync record, and reuse it from `update_templates()`.
- [x] **Run**: `uv run pytest tests/test_templates.py::TestUpdateTemplates::test_update_templates_ignores_mtime_when_workspace_matches_saved_base -v`

### Component: First-load reconciliation wiring

- [x] **Test**: `test_context_loader_reconciles_templates_before_first_load()` - verify a fresh `ContextLoader` with a shared cache dir reads the refreshed content on the first load after a template change.
- [x] **Implement**: add `cache_dir` injection to `ContextLoader`, call the merge-aware reconciliation helper before reading a context file, and keep the path idempotent.
- [x] **Run**: `uv run pytest tests/test_context_integration.py::TestContextLoaderTemplateAutoCreation::test_context_loader_reconciles_templates_before_first_load -v`

---

## Progress Summary

Phase 3 is complete.
- [x] Fast-forward clean restart state complete.
- [x] First-load reconciliation wiring complete.

Continue with Milestone 4: Write standard conflict markers on merge failure in `prds/148-template-sync-merge-conflicts.md`.

## Files to Modify

1. `src/alfred/templates.py` — add merge-aware per-template sync logic and reuse it from update paths
2. `src/alfred/context.py` — inject cache control and trigger reconciliation before context loads
3. `tests/test_templates.py` — clean restart merge regression coverage
4. `tests/test_context_integration.py` — first-load reconciliation regression coverage

## Commit Strategy

Each completed checkbox should be one atomic commit:
- `test(templates): cover clean restart fast-forward sync`
- `feat(templates): reconcile clean restart template changes`
- `test(context): cover first-load template reconciliation`
- `feat(context): reconcile templates before context loading`

## Exit Criteria for Milestone 3

- Alfred fast-forwards clean template drift on restart without relying on mtimes alone
- The first context load after restart sees the reconciled content
- Sync state is refreshed after a clean auto-merge
- Milestone 4 can layer conflict-marker output on top of the shared reconciliation helper
