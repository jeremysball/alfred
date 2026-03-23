# Execution Plan: PRD #148 - Milestone 5: Block Conflicted Files from Context Loading

## Overview
Keep conflicted managed templates out of the active prompt path while exposing an explicit blocked-state signal to callers. This phase should reuse the existing sync store as the source of truth and keep the new state local to `ContextLoader` and the returned context objects.

---

## Phase 5: Fail closed on conflicted context files

### Component: Block managed files at load time

- [x] **Test**: `test_load_file_marks_conflicted_managed_template_as_blocked()` - verify a fresh `ContextLoader` with a shared cache dir returns a blocked `ContextFile` state for a conflicted managed template and does not auto-create the file if it has been removed
- [x] **Implement**: add `ContextFileState` and blocked-state tracking in `ContextLoader`, check `TemplateManager.get_sync_record()` after reconciliation, and skip managed-file auto-create when the sync record is conflicted
- [x] **Run**: `uv run pytest tests/test_context_integration.py::TestContextLoaderBlockedTemplates::test_load_file_marks_conflicted_managed_template_as_blocked -v`

### Component: Exclude blocked files from assembly and surface them explicitly

- [x] **Test**: `test_assemble_excludes_blocked_context_files_and_records_blocked_context_files()` - verify `assemble()` omits blocked files from the system prompt, keeps clean files intact, and reports the blocked file names in the assembled context metadata
- [x] **Implement**: filter blocked files out of prompt assembly, populate `blocked_context_files` on `AssembledContext`, and expose the current blocked list from `ContextLoader`
- [x] **Run**: `uv run pytest tests/test_context_integration.py::TestContextLoaderBlockedTemplates::test_assemble_excludes_blocked_context_files_and_records_blocked_context_files tests/test_system_md_integration.py -q`

### Component: Ensure search assembly respects the same blocked-file filter

- [x] **Test**: `test_assemble_with_search_excludes_blocked_context_files()` - verify `assemble_with_search()` omits blocked files from the system prompt so chat paths use the same fail-closed state as `/context`
- [x] **Implement**: reuse the same loaded-file assembly path inside `assemble_with_search()` so blocked managed files cannot bypass the fail-closed gate
- [x] **Run**: `uv run pytest tests/test_context_integration.py::TestContextLoaderBlockedTemplates::test_assemble_with_search_excludes_blocked_context_files -q`

---

## Progress Summary

Milestone 5 is complete.
Continue with Milestone 6: Surface persistent warnings in the WebUI and `/context` in `prds/148-template-sync-merge-conflicts.md`.

## Files to Modify

1. `src/alfred/context.py` — add blocked-state metadata and filter blocked context files from assembly
2. `tests/test_context_integration.py` — regression coverage for blocked loading and blocked assembly

## Commit Strategy

Each completed checkbox should be one atomic commit:
- `test(context): cover blocked managed template loading`
- `feat(context): block conflicted templates from prompt assembly`
- `test(context): cover blocked context assembly`
- `feat(context): surface blocked context files in assembled context`

## Exit Criteria for Milestone 5

- Conflicted managed templates do not enter active prompt assembly
- `ContextLoader` exposes an explicit blocked state for affected files
- Clean context files continue to assemble normally
- Milestone 6 can build warning surfaces from the same blocked-state signal
