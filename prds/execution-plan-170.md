# Execution Plan: PRD #170 - Web UI Bootstrap and Script Loading Cleanup

## Overview
Move Web UI startup ownership out of `index.html` and into one deterministic bootstrap path without changing product behavior. Start by making bootstrap state and readiness observable. Then switch the page to one runtime entry module, move core and optional registration behind explicit bootstrap steps, and finally delete the redundant HTML and auto-run wiring that still controls startup order.

## Current Repo Constraints
- `src/alfred/interfaces/webui/static/index.html` still loads a long runtime chain of component scripts, feature bundles, config/logger scripts, and self-starting modules. Startup correctness depends on script tag order and mixed classic/module loading.
- `src/alfred/interfaces/webui/static/js/main.js` still auto-runs on import via a DOM-ready block and owns most feature initialization directly. Bootstrap extraction must avoid double initialization while preserving `window.__alfredWebUI` and `window.alfredWebSocketClient` for existing browser tests.
- Several feature entrypoints still publish and consume `window.*` registries or helpers (`CommandPaletteLib`, `ShortcutRegistry`, `ContextMenuLib`, `NotificationsLib`, `DragDropLib`, `PullToRefresh`, `kidcoreAudioManager`). Order still matters until later PRDs remove those globals.
- Browser tests currently wait on incidental signals such as `window.__alfredWebUI?.getComposerState?.()` or feature-specific globals. There is no single ready or failed bootstrap seam.
- Runtime config and client logging must still load before the app runtime. `/app-config.js` currently emits `window.__ALFRED_WEBUI_CONFIG__`, while some modules still read `window.APP_CONFIG`, so the bootstrap work must keep config availability explicit.

## Success Signal
- Visiting `/static/index.html` boots the page through one bootstrap-owned runtime entry module.
- Browser tests can wait on one deterministic bootstrap status seam and can see the last completed or failed phase.
- Core chat behavior still works: the composer becomes idle, the WebSocket client connects, and sending a message emits `chat.send`.
- Optional features attach through explicit bootstrap registration instead of direct HTML ordering.
- `index.html` is reduced to document structure, styles, shell prerequisites, config/logger scripts, and one runtime entry module.

## Validation Workflow
- **Workflow:** Both
- **JavaScript:** `npm run js:check`
- **Python:** `uv run ruff check src/ && uv run mypy --strict src/`
- **Targeted browser checks for this PRD:**
  - `uv run pytest tests/webui/test_bootstrap.py tests/webui/test_frontend.py tests/webui/test_frontend_logging.py -v`
  - add targeted feature smoke tests only for the bootstrap paths touched in the phase

---

## Phase 1: Milestone 1 - Define the bootstrap contract

### Bootstrap status and ready seam

- [x] Test: `test_bootstrap_ready_seam_reports_phase_progress()` - verify browser tests can observe bootstrap phases and wait for a single interactive-ready seam instead of inferring readiness from `getComposerState()`.
- [x] Implement: add a bootstrap-owned status surface that tracks ordered phases, exposes readiness through `window.__alfredWebUI`, and documents the phase contract plus core-vs-optional split in `docs/ARCHITECTURE.md` and `prds/170-web-ui-bootstrap-and-script-loading-cleanup.md`.
- [x] Run: `uv run pytest tests/webui/test_bootstrap.py::test_bootstrap_ready_seam_reports_phase_progress -v`

### Failure visibility

- [ ] Test: `test_bootstrap_reports_failed_phase_when_registered_step_throws()` - verify startup reports the failing phase locally instead of hanging silently when a bootstrap step throws.
- [ ] Implement: wrap bootstrap steps with explicit phase tracking and failure reporting while still failing loudly in the browser console for local debugging.
- [ ] Run: `uv run pytest tests/webui/test_bootstrap.py::test_bootstrap_reports_failed_phase_when_registered_step_throws -v`

---

## Phase 2: Milestone 2 - Introduce a single app entrypoint

### Runtime-owned page startup

- [ ] Test: `test_page_boots_via_single_runtime_entrypoint()` - verify the real page becomes interactive and sending a message still emits `chat.send` when startup is driven by one bootstrap-owned runtime entry module.
- [ ] Implement: add `src/alfred/interfaces/webui/static/js/app/bootstrap.js`, make `main.js` callable from bootstrap instead of auto-running on import, and move DOM-ready ownership into the bootstrap path.
- [ ] Run: `uv run pytest tests/webui/test_bootstrap.py::test_page_boots_via_single_runtime_entrypoint -v`

### HTML shell ownership

- [ ] Test: `test_index_html_loads_single_runtime_entry_module_after_config_and_logger()` - verify `index.html` keeps config and logger scripts ahead of exactly one runtime entry module and no longer lists the runtime feature chain.
- [ ] Implement: reduce `src/alfred/interfaces/webui/static/index.html` to shell concerns plus the single runtime entry module, preserving only true shell prerequisites such as DOM structure, CSS, and any browser-required static assets.
- [ ] Run: `uv run pytest tests/webui/test_frontend_logging.py::test_index_html_loads_single_runtime_entry_module_after_config_and_logger -v`

---

## Phase 3: Milestone 3 - Migrate runtime registration into the bootstrap path

### Core registration path

- [ ] Test: `test_core_runtime_reaches_ready_through_bootstrap_registry()` - verify the bootstrap path registers the components and core runtime surfaces needed for `window.__alfredWebUI`, WebSocket send, and chat interactivity before it reports ready.
- [ ] Implement: move component registration, core service startup, and chat/runtime initialization into explicit bootstrap-owned core steps while keeping current compatibility globals intact.
- [ ] Run: `uv run pytest tests/webui/test_bootstrap.py::test_core_runtime_reaches_ready_through_bootstrap_registry -v`

### Command and search surfaces

- [ ] Test: update `tests/webui/test_leader_keybinds.py::test_leader_palette_command_palette` and `tests/webui/test_leader_keybinds.py::test_leader_quick_switcher` to rely on the bootstrap seam and verify command palette and quick-switcher registration still work after startup moves.
- [ ] Implement: move keyboard, command palette, search, and related core interaction startup out of HTML ordering and into explicit core registration steps.
- [ ] Run: `uv run pytest tests/webui/test_leader_keybinds.py::test_leader_palette_command_palette tests/webui/test_leader_keybinds.py::test_leader_quick_switcher -v`

### Optional feature registration

- [ ] Test: update `tests/webui/test_mobile_gestures.py::test_desktop_no_gesture_attachment` to verify optional mobile startup still behaves correctly when gestures are registered through bootstrap instead of direct script ordering.
- [ ] Implement: move optional feature startup for mobile gestures, PWA/offline, drag-drop, and other auxiliary modules behind explicit optional registration steps that cannot silently corrupt core boot.
- [ ] Run: `uv run pytest tests/webui/test_mobile_gestures.py::test_desktop_no_gesture_attachment -v`

---

## Phase 4: Milestone 4 - Delete redundant script-order wiring

### Remove duplicate runtime entry paths

- [ ] Test: `test_runtime_does_not_double_initialize_when_bootstrap_imports_main()` - verify the page initializes once and does not duplicate listeners or startup side effects when `main.js` is loaded through bootstrap.
- [ ] Implement: delete the DOM-ready auto-run block from `main.js` and remove any remaining duplicate runtime path that competes with bootstrap ownership.
- [ ] Run: `uv run pytest tests/webui/test_bootstrap.py::test_runtime_does_not_double_initialize_when_bootstrap_imports_main -v`

### Document-shell regression

- [ ] Test: `test_index_html_is_document_shell_for_runtime_startup()` - verify `index.html` still provides the chat DOM and shell assets but no longer orchestrates component or feature runtime ordering.
- [ ] Implement: remove redundant runtime `<script>` tags and any HTML-owned startup wiring once the bootstrap path is authoritative.
- [ ] Run: `uv run pytest tests/webui/test_frontend.py::test_index_html_is_document_shell_for_runtime_startup -v`

---

## Phase 5: Milestone 5 - Regression coverage and documentation

### Contract and smoke regression alignment

- [ ] Test: update the touched browser tests to wait on the explicit bootstrap seam and add one focused regression for each moved boundary rather than relying on one broad startup smoke test.
- [ ] Implement: align `tests/webui/test_bootstrap.py`, `tests/webui/test_frontend.py`, `tests/webui/test_frontend_logging.py`, and the touched feature smoke tests with the new startup contract; keep the docs and PRD decisions in sync with the final ownership boundary.
- [ ] Run: `uv run pytest tests/webui/test_bootstrap.py tests/webui/test_frontend.py tests/webui/test_frontend_logging.py tests/webui/test_leader_keybinds.py::test_leader_palette_command_palette tests/webui/test_leader_keybinds.py::test_leader_quick_switcher tests/webui/test_mobile_gestures.py::test_desktop_no_gesture_attachment -v`

### Final validation

- [ ] Run: `npm run js:check && uv run ruff check src/ && uv run mypy --strict src/ && uv run pytest tests/webui/test_bootstrap.py tests/webui/test_frontend.py tests/webui/test_frontend_logging.py tests/webui/test_leader_keybinds.py::test_leader_palette_command_palette tests/webui/test_leader_keybinds.py::test_leader_quick_switcher tests/webui/test_mobile_gestures.py::test_desktop_no_gesture_attachment -v`

---

## Files to Modify

1. `src/alfred/interfaces/webui/static/index.html` - reduce to document shell plus one runtime entry module
2. `src/alfred/interfaces/webui/static/js/main.js` - stop auto-running and expose bootstrap-callable startup
3. `src/alfred/interfaces/webui/static/js/app/bootstrap.js` - new deterministic bootstrap entrypoint
4. `src/alfred/interfaces/webui/static/js/app/registry.js` - possible step registry for core and optional startup
5. `src/alfred/interfaces/webui/static/js/app/ready.js` - possible shared bootstrap status or ready helper
6. `src/alfred/interfaces/webui/static/js/features/**/index.js` - touched feature entrypoints that still depend on HTML order or global registration timing
7. `tests/webui/test_bootstrap.py` - bootstrap seam, entrypoint, and double-init regressions
8. `tests/webui/test_frontend.py` - document-shell regression coverage
9. `tests/webui/test_frontend_logging.py` - shell load-order contract
10. `tests/webui/test_leader_keybinds.py` - core command and keyboard smoke after registration moves
11. `tests/webui/test_mobile_gestures.py` - optional feature smoke after registration moves
12. `docs/ARCHITECTURE.md` - bootstrap contract and ownership notes
13. `prds/170-web-ui-bootstrap-and-script-loading-cleanup.md` - decision log and implementation notes

## Commit Strategy

Each completed test → implement → run block should become one atomic commit:
- `test(webui): add bootstrap ready seam coverage`
- `fix(webui): route startup through a single bootstrap entrypoint`
- `refactor(webui): move core startup behind bootstrap registration`
- `fix(webui): move optional feature boot behind explicit registration`
- `fix(webui): delete legacy html startup ordering`
- `docs(webui): document bootstrap ownership and readiness`
