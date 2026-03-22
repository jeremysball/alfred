# Execution Plan: PRD #143 - Milestone 6

## Overview

Verify the user-visible path and close the loop with documentation and a full repository verification sweep.

---

## Milestone 6: Add Web UI regression coverage and finalize verification

### Component: Web UI remember → recall → reload behavior

- [ ] **Test**: `test_webui_memory_recall_survives_reload_with_correct_similarity_semantics()`
  - Add a browser- or websocket-level test under `tests/webui/`
  - Save a memory, trigger recall, reload the page/session, and verify recall still works
- [ ] **Implement**: add the smallest test harness support needed to exercise the real Web UI path
  - Keep production changes limited to bug fixes required by the behavior test
- [ ] **Run**: `uv run pytest tests/webui/test_memory_recall_semantics.py -q --timeout=30`

### Component: Search-regression integration sweep

- [ ] **Test**: `test_memory_and_session_search_share_the_same_similarity_direction()`
  - Add an integration test that exercises both paths in one scenario
- [ ] **Implement**: remove any remaining call-site inconsistencies surfaced by the integration test
- [ ] **Run**: `uv run pytest tests/test_memory_integration.py tests/test_search_sessions_integration.py -q`

### Component: Documentation and maintenance notes

- [ ] **Refactor**: update inline comments or nearby docs where vector search semantics were previously ambiguous
  - Keep the authoritative design in `prds/143-cosine-similarity-migration.md`
- [ ] **Run**: `uv run ruff check src/ tests/`

### Component: Final verification sweep

- [ ] **Run**: `uv run mypy --strict src/`
- [ ] **Run**: `uv run pytest`
- [ ] **Run**: `uv run alfred webui --port 8080`

---

## Files to Modify

1. `tests/webui/test_memory_recall_semantics.py` - new Web UI regression behavior test
2. `tests/test_memory_integration.py` - cross-path integration assertions if needed
3. `tests/test_search_sessions_integration.py` - cross-path integration assertions if needed
4. `prds/143-cosine-similarity-migration.md` - keep acceptance criteria/progress accurate if scope shifts during implementation
5. any touched source files required to satisfy the behavior test

## Commit Strategy

Suggested atomic commits:
- `test(webui): cover memory recall reload regression`
- `test(search): verify memory and session similarity direction`
- `docs(storage): clarify cosine similarity contract`
- `chore: run final verification for prd 143`