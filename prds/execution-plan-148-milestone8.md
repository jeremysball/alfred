# Execution Plan: PRD #148 - Milestone 8: Documentation and Operator Guidance

## Overview
Milestone 8 turns the finalized template sync behavior into operator-facing documentation. The docs should explain where sync state lives, how restart reconciliation works, what the git-style conflict markers mean, how blocked files are surfaced, and how to recover after a manual fix.

This phase is documentation-first and test-first. The tests pin the expected wording and cross-references so the guide, README, and architecture docs stay aligned with the implemented behavior.

---

## Phase 8: Document template sync and conflict recovery

### Component: Dedicated operator guide

- [x] **Test**: `test_template_sync_guide_documents_sync_store_conflicts_and_recovery()` - verify the new guide covers the cache location, clean restart reconciliation, git-style conflict markers, fail-closed blocked files, warning surfaces, and manual recovery steps
- [x] **Implement**: create `docs/template-sync.md` as the canonical operator guide for template sync and conflict resolution
- [x] **Run**: `uv run pytest tests/test_template_sync_docs.py::test_template_sync_guide_documents_sync_store_conflicts_and_recovery -v`

### Component: README entry point

- [x] **Test**: `test_readme_links_to_template_sync_guide()` - verify README links to the new guide from the documentation section and identifies it as the conflict-recovery reference
- [x] **Implement**: update `README.md` to surface the new template-sync guide for users who need setup or recovery instructions
- [x] **Run**: `uv run pytest tests/test_template_sync_docs.py::test_readme_links_to_template_sync_guide -v`

### Component: Architecture summary

- [ ] **Test**: `test_architecture_doc_mentions_workspace_scoped_sync_records_and_blocked_files()` - verify `docs/ARCHITECTURE.md` explains restart-time reconciliation, workspace-scoped sync records, blocked-file behavior, and the shared warning surfaces
- [ ] **Implement**: update `docs/ARCHITECTURE.md` to reflect the final sync contract and link to the operator guide
- [ ] **Run**: `uv run pytest tests/test_template_sync_docs.py::test_architecture_doc_mentions_workspace_scoped_sync_records_and_blocked_files -v`

---

## Files to Modify

1. `docs/template-sync.md` - new operator guide for sync metadata, conflict markers, and recovery
2. `README.md` - docs index entry and user-facing pointer to the guide
3. `docs/ARCHITECTURE.md` - architecture summary of restart reconciliation and warning surfaces
4. `tests/test_template_sync_docs.py` - new documentation assertions for the guide and cross-references

## Commit Strategy

Each checkbox should be one atomic commit following conventional commits:
- `test(docs): pin template sync guide content`
- `docs(template-sync): add operator guide for conflict recovery`
- `test(docs): pin template sync references in README and architecture`
- `docs(readme): link template sync guide`
- `docs(architecture): summarize restart reconciliation and warnings`

## Exit Criteria for Milestone 8

- The operator guide explains template sync without source spelunking
- README points users to the guide from the docs index
- Architecture docs describe restart reconciliation, blocked files, and persistent warnings
- Documentation assertions keep the guide and cross-references from drifting
