# Execution Plan: PRD #148 - Milestone 4: Standard Conflict Markers

## Overview
When a managed template and its workspace copy both diverge from the saved base snapshot, Alfred should write standard git conflict markers into the workspace file and mark the sync record conflicted.

---

## Milestone 4: Write standard conflict markers on merge failure

### Component: Conflict marker output and sync-state persistence

- [x] **Test**: `test_update_templates_writes_standard_conflict_markers_when_template_and_workspace_both_diverge()` - verify a restart-time reconciliation writes `<<<<<<< ours`, `=======`, and `>>>>>>> theirs` into the workspace file when both sides changed from the saved base snapshot, and marks the sync record conflicted
- [x] **Implement**: add a conservative conflict-writing path in `TemplateManager.reconcile_template()` that preserves the last clean base snapshot, writes standard git markers, and persists `TemplateSyncState.CONFLICTED`
- [x] **Run**: `uv run pytest tests/test_templates.py::TestUpdateTemplates::test_update_templates_writes_standard_conflict_markers_when_template_and_workspace_both_diverge -v`

---

## Progress Summary

Milestone 4 is complete.
Continue with Milestone 5: Block conflicted files from context loading in `prds/148-template-sync-merge-conflicts.md`.

## Files to Modify

1. `src/alfred/templates.py` — write conflict markers and persist conflicted sync records
2. `tests/test_templates.py` — add regression coverage for the merge-failure path

## Commit Strategy

Each completed checkbox should be one atomic commit:
- `test(templates): cover conflict-marker sync failures`
- `feat(templates): write standard conflict markers on merge failure`

## Exit Criteria for Milestone 4

- Divergent workspace/template files are written with standard git conflict markers
- The sync record is marked conflicted and keeps the last clean base snapshot
- Milestone 5 can block conflicted files from context loading
