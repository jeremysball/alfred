# Execution Plan: PRD #148 - Milestone 7: Regression Tests for Sync, Conflict, and Fail-Closed Paths

## Overview
Milestone 6 already surfaced the blocked-file warning path. Milestone 7 should pin the remaining restart-sensitive regressions so template sync stays safe across clean updates, manual conflict resolution, and workspace isolation.

This phase is intentionally test-first. Production behavior should already be in place; these tasks add explicit guards around the edge cases that are easiest to regress.

---

## Phase 7: Pin the restart and recovery regressions

### Component: Clean restart merge path

- [x] **Test**: `test_template_manager_fast_forwards_clean_update_after_restart()` - verify a fresh `TemplateManager` can recover the saved base snapshot from cache and still fast-forward a clean update when the template changes after restart
- [x] **Implement**: add a restart-style regression in `tests/test_templates.py` that creates the file, instantiates a new manager with the same cache directory, mutates the template, and asserts `update_templates()` writes the upstream content and refreshes the base snapshot
- [x] **Run**: `uv run pytest tests/test_templates.py::TestUpdateTemplates::test_template_manager_fast_forwards_clean_update_after_restart -v`

### Component: Conflict recovery clears blocked state

- [x] **Test**: `test_load_file_reenables_manually_resolved_conflicted_template()` - verify a conflicted managed file becomes active again after the user resolves the file on disk and Alfred restarts
- [x] **Implement**: add a regression in `tests/test_context_integration.py` that seeds a conflicted template, rewrites the workspace file with a clean merged result, reloads with a fresh `ContextLoader`, and asserts the file returns as `ACTIVE` with no blocked-context entry
- [x] **Run**: `uv run pytest tests/test_context_integration.py::TestContextLoaderBlockedTemplates::test_load_file_reenables_manually_resolved_conflicted_template -v`

### Component: Workspace-scoped sync metadata stays isolated

- [ ] **Test**: `test_template_manager_ignores_sync_record_from_other_workspace()` - verify a sync record from one workspace does not leak into a different workspace that happens to share the same cache directory
- [ ] **Implement**: add a regression in `tests/test_templates.py` that seeds a sync record in workspace A, constructs a manager for workspace B with the same cache file, and asserts `get_sync_record()` returns `None` for the foreign record
- [ ] **Run**: `uv run pytest tests/test_templates.py::TestTemplateManagerIntegration::test_template_manager_ignores_sync_record_from_other_workspace -v`

---

## Files to Modify

1. `tests/test_templates.py` — add the clean-restart and workspace-isolation regression tests
2. `tests/test_context_integration.py` — add the manual-conflict-resolution recovery regression test

## Commit Strategy

Each checkbox should be one atomic commit following conventional commits:
- `test(templates): pin restart fast-forward sync behavior`
- `test(context): verify conflicted templates unblock after manual resolution`
- `test(templates): ignore sync records from other workspaces`

## Exit Criteria for Milestone 7

- Clean updates still fast-forward after a restart and refresh the stored base snapshot
- Manually resolved conflicted files become active again instead of staying blocked
- Sync metadata from one workspace cannot contaminate another workspace
- The Milestone 5/6 fail-closed behavior stays covered by the existing regression suite
