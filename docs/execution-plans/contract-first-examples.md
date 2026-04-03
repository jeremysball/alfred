# Contract-First Execution Plan Examples

These examples teach execution-plan quality by contrast.

Use them when writing or reviewing a PRD execution plan. The point is not to copy the exact filenames or test names. The point is to prefer:

- observable behavior over implementation shape
- phase contracts over invented architecture
- boundary-sized tasks over catch-all smoke tests
- explicit workflow choice over vague validation

If an execution plan feels ambiguous, follow the examples in this file.

---

## Example 1: Frontend Bootstrap Refactor

**Scenario:** Move startup ownership from HTML into one JavaScript bootstrap path without changing user-visible behavior.

**Validation workflow:** Both
- `npm run js:check`
- targeted browser tests in `tests/webui/`

### Bad

```markdown
## Phase 1: Bootstrap Foundation

- [ ] Test: `test_bootstrap_module_exports()` - verify `bootstrap.js` exports `initApp()`
- [ ] Implement: create `js/app/bootstrap.js` and export `initApp()`
- [ ] Run: `npm run js:check`

- [ ] Test: `test_app_directory_exists()` - verify `js/app/` exists
- [ ] Implement: create `js/app/`
- [ ] Run: `ls js/app/`
```

### Why it fails

- proves file shape, not startup behavior
- spends plan budget on directory creation and exports
- does not prove that HTML stopped owning runtime ordering
- does not create a browser-visible readiness seam

### Better

```markdown
## Current Repo Constraints
- `index.html` still controls script order
- `main.js` auto-runs on import
- browser tests do not have one deterministic ready seam

## Success Signal
- the page boots through one runtime entrypoint
- tests can wait on `window.__alfredWebUI.ready`

## Phase 1: Bootstrap-Owned Startup Path

- [ ] Test: `test_page_boots_via_runtime_entrypoint()` - verify the chat UI becomes interactive when startup is driven by the bootstrap path
- [ ] Implement: add a thin bootstrap entrypoint that preserves current startup order while moving runtime ownership out of HTML
- [ ] Run: `uv run pytest tests/webui/test_bootstrap.py::test_page_boots_via_runtime_entrypoint -v`

## Phase 2: Deterministic Ready Seam

- [ ] Test: `test_ready_promise_resolves_when_app_is_interactive()` - verify tests can wait on `window.__alfredWebUI.ready`
- [ ] Implement: expose a single ready promise from the bootstrap path after the existing app init completes
- [ ] Run: `uv run pytest tests/webui/test_bootstrap.py::test_ready_promise_resolves_when_app_is_interactive -v`

## Phase 3: HTML Shell Cleanup

- [ ] Test: `test_index_html_no_longer_owns_runtime_ordering()` - verify runtime script ordering moved out of HTML and page still boots
- [ ] Implement: reduce `index.html` to document shell concerns plus the explicit runtime entrypoint
- [ ] Run: `uv run pytest tests/webui/test_frontend.py::test_index_html_no_longer_owns_runtime_ordering -v`
```

### Why it works

- starts from the contract the user and tests can observe
- keeps the scope on PRD behavior, not future architecture
- breaks the refactor into real boundaries: startup path, ready seam, HTML ownership
- uses the smallest meaningful validation for each step

---

## Example 2: Backend Storage Migration

**Scenario:** Move session summaries to a new storage backend while preserving behavior for callers.

**Validation workflow:** Python
- `uv run ruff check src/ tests/`
- `uv run mypy --strict src/`
- targeted pytest for the touched storage and caller surfaces

### Bad

```markdown
## Phase 1: Storage Layer

- [ ] Test: `test_summary_store_class_exists()` - verify `SummaryStore` exists
- [ ] Implement: create `src/storage/summary_store.py`
- [ ] Run: `uv run pytest tests/storage/test_summary_store.py -v`

- [ ] Test: `test_repository_methods_exist()` - verify `save()` and `load()` exist
- [ ] Implement: add `save()` and `load()` methods
- [ ] Run: `uv run pytest tests/storage/test_summary_store.py -v`
```

### Why it fails

- proves a class and methods exist, not that the migration is safe
- hides the caller contract behind abstraction talk
- does not name the risky constraints, such as old call sites or serialization differences

### Better

```markdown
## Current Repo Constraints
- existing callers expect summary content, timestamps, and embeddings to round-trip unchanged
- old storage logic is still used in production paths
- migration risk is data-shape drift, not missing classes

## Success Signal
- existing callers can save and read summaries through the new store with no behavior change

## Phase 1: Round-Trip Contract

- [ ] Test: `test_summary_round_trip_through_new_store()` - verify content, timestamps, embeddings, and ordering survive a save/load cycle through the new store boundary
- [ ] Implement: add the minimal persistence adapter needed for the new backend to satisfy the current caller contract
- [ ] Run: `uv run pytest tests/storage/test_summary_store.py::test_summary_round_trip_through_new_store -v`

## Phase 2: Caller Migration

- [ ] Test: `test_session_service_reads_summaries_through_new_store()` - verify the public session surface still returns the expected summary data
- [ ] Implement: switch the existing caller to the new store without changing its public behavior
- [ ] Run: `uv run pytest tests/sessions/test_session_service.py::test_session_service_reads_summaries_through_new_store -v`
```

### Why it works

- tests the contract at the storage seam and the caller seam
- keeps the migration minimal
- proves the PRD outcome instead of proving that a new module was created

---

## Example 3: CLI or TUI Lifecycle Bug

**Scenario:** Fix quitting interactive mode so the terminal returns cleanly and background tasks shut down.

**Validation workflow:** Python
- `uv run ruff check src/ tests/`
- `uv run mypy --strict src/`
- targeted CLI or TUI lifecycle tests
- actually launch the app before claiming done

### Bad

```markdown
## Phase 1: Controller Cleanup

- [ ] Test: `test_session_controller_exports_shutdown()` - verify `shutdown()` exists
- [ ] Implement: add `shutdown()` to `SessionController`
- [ ] Run: `uv run pytest tests/test_cli.py -v`

- [ ] Test: `test_cleanup_manager_exists()` - verify a cleanup helper is created
- [ ] Implement: add `CleanupManager`
- [ ] Run: `uv run pytest tests/test_cli.py -v`
```

### Why it fails

- lifecycle bugs are not fixed by proving a helper exists
- introduces abstractions before proving the quit path works
- uses broad tests instead of the real failing surface

### Better

```markdown
## Current Repo Constraints
- quitting can leave background tasks running
- terminal state restoration is easy to miss in unit-only tests
- this surface is sensitive to actual lifecycle order

## Success Signal
- quitting interactive mode returns the terminal to a clean prompt and no background tasks remain

## Phase 1: Quit Path Behavior

- [ ] Test: `test_quit_restores_terminal_and_stops_background_tasks()` - verify quitting from the public interactive path restores terminal state and cleans up background tasks
- [ ] Implement: add the minimum cleanup in the real quit path
- [ ] Run: `uv run pytest tests/tui/test_runtime.py::test_quit_restores_terminal_and_stops_background_tasks -v`

## Phase 2: Real Runtime Verification

- [ ] Test: launch the app and quit interactively
- [ ] Implement: fix any remaining lifecycle gaps exposed by the real runtime
- [ ] Run: `uv run pytest tests/tui/test_runtime.py -v`
```

### Why it works

- tests the real lifecycle contract
- keeps the implementation small
- matches the repo rule that TUI and CLI changes must be exercised through the actual runtime

---

## Common Review Questions

Before approving an execution plan, ask:

1. Does each phase establish a contract someone can observe?
2. Is the plan proving the PRD outcome or just proving that new files and exports exist?
3. Are broad refactors split by boundary?
4. Did the plan choose Python, JavaScript, or both explicitly?
5. If the plan introduces new architecture, is that the minimum needed for this PRD, or is it drift from a later PRD?
