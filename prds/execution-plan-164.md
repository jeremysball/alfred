# Execution Plan: PRD #164 - Repo-wide ESM Migration for JavaScript

## Overview
Milestone 1 (AGENTS policy) is already complete. The remaining work is to finish the browser module bootstrap that is still breaking the Web UI, then migrate the JS test helpers and add a repo-wide ESM gate so the migration stays complete.

---

## Phase 1: Core browser bootstrap

### WebSocket client and offline module cleanup

- [ ] Test: `test_streaming_composer_keyboard_contract()` - verify the real page boots, `window.__alfredWebUI` is defined, composer state is reachable, and send / queue / edit flows still work after the bootstrap changes
- [x] Smoke test: `test_webui_bootstrap_allows_message_send()` - verify the real page boots, `window.__alfredWebUI` is defined, and `chat.send` is emitted after sending a message
- [x] Implement: import `AlfredWebSocketClient` directly in `src/alfred/interfaces/webui/static/js/main.js`; remove the classic `websocket-client.js` script tag from `src/alfred/interfaces/webui/static/index.html`; delete the CSS import from `src/alfred/interfaces/webui/static/js/features/offline/index.js` so the module graph is browser-safe
- [ ] Run: `uv run pytest tests/webui/test_streaming_composer.py::test_streaming_composer_keyboard_contract -v`

Progress note:
- The fix also needed `initializeGestures as initializeMobileGestures` in `main.js` and `.search-overlay.hidden { display: none !important; }` in `src/alfred/interfaces/webui/static/js/features/search/styles.css`.
- The original keyboard-contract test still fails later on stale edit assertions, so the narrower bootstrap smoke test is the current green signal.

---

## Phase 2: Feature bundle module entrypoints

### Command palette, keyboard, context menu, notifications, drag-drop

- [ ] Test: `test_webui_bootstraps_without_module_load_errors()` - launch the real Web UI in Playwright, assert `window.__alfredWebUI` exists, assert the feature libs are present (`window.CommandPaletteLib`, `window.ShortcutRegistry`, `window.ContextMenuLib`, `window.NotificationsLib`, `window.DragDropLib`), and fail on `Failed to load module script`, `Unexpected token 'export'`, or `Cannot use import statement outside a module`
- [ ] Implement: refactor `src/alfred/interfaces/webui/static/js/features/{command-palette,keyboard,context-menu,notifications,drag-drop}/index.js` to import their local submodules directly instead of reading from `window.*` bridges; update `src/alfred/interfaces/webui/static/index.html` to load those entrypoints as `type="module"`; remove the individual submodule `<script>` tags and the redundant `pull-to-refresh.js` classic load
- [ ] Run: `uv run pytest tests/webui/test_bootstrap.py -v && uv run pytest tests/webui/test_streaming_composer.py::test_streaming_composer_keyboard_contract -v`

---

## Phase 3: JS test helper migration

### WebSocket protocol helper

- [ ] Test: `test_websocket_client_uses_esm_import()` - verify the protocol helper can load `websocket-client.js` without CommonJS `require()`
- [ ] Implement: update `tests/webui/test_websocket_client_protocol.py` to use `node --input-type=module` and dynamic `import()` (or equivalent) instead of `require('./src/alfred/interfaces/webui/static/js/websocket-client.js')`
- [ ] Run: `uv run pytest tests/webui/test_websocket_client_protocol.py -v`

### Browser-side JS test scripts

- [ ] Test: `test_no_browser_js_test_files_use_commonjs()` - verify the browser-side `src/alfred/interfaces/webui/static/js/features/**/test-*.js` helpers contain no `require()` / `module.exports`
- [ ] Implement: convert or delete the remaining browser-side JS test helpers under `src/alfred/interfaces/webui/static/js/features/` to native ESM test modules, and remove any last CommonJS snippets
- [ ] Run: `uv run pytest tests/test_js_esm_policy.py -v`

---

## Phase 4: Repo-wide ESM gate and final validation

### CommonJS scan gate

- [ ] Test: `test_repo_has_no_commonjs_js_modules()` - scan the repository for `require()` / `module.exports` in `.js` files outside docs and generated artifacts
- [ ] Implement: fix any residual CommonJS surfaces surfaced by the scan
- [ ] Run: `rg -n "require\\(|module\\.exports" . --glob '*.js' --glob '!**/.venv/**' --glob '!**/node_modules/**' -S`

### Final validation

- [ ] Test: full Web UI and repo validation
- [ ] Implement: address any regressions uncovered by the suite
- [ ] Run: `uv run ruff check src/ && uv run mypy --strict src/ && uv run pytest -m "not slow"`

---

## Files to Modify

1. `src/alfred/interfaces/webui/static/js/main.js` - import the WebSocket client directly so the module bootstrap is self-contained
2. `src/alfred/interfaces/webui/static/js/features/offline/index.js` - remove the browser-incompatible CSS import
3. `src/alfred/interfaces/webui/static/index.html` - load module entrypoints instead of classic ESM submodule scripts
4. `src/alfred/interfaces/webui/static/js/features/search/styles.css` - hide the closed quick-switcher overlay so it does not block the send button
5. `src/alfred/interfaces/webui/static/js/features/command-palette/index.js` - replace the window bridge with direct imports
6. `src/alfred/interfaces/webui/static/js/features/keyboard/index.js` - replace the window bridge with direct imports
7. `src/alfred/interfaces/webui/static/js/features/context-menu/index.js` - replace the window bridge with direct imports
8. `src/alfred/interfaces/webui/static/js/features/notifications/index.js` - replace the window bridge with direct imports
9. `src/alfred/interfaces/webui/static/js/features/drag-drop/index.js` - replace the window bridge with direct imports
10. `tests/webui/test_bootstrap.py` - new browser smoke test for page boot, `window.__alfredWebUI`, and `chat.send`
11. `tests/webui/test_websocket_client_protocol.py` - migrate the Node helper to ESM
12. `tests/test_js_esm_policy.py` - new repo-wide CommonJS gate
13. `src/alfred/interfaces/webui/static/js/features/**/test-*.js` - browser-side JS test helpers to convert or delete

## Commit Strategy

Each checkbox = one atomic commit following conventional commits:
- `fix(webui): import websocket client into the ESM bootstrap`
- `fix(webui): load feature bundles through module entrypoints`
- `test(webui): verify browser bootstrap and feature-lib availability`
- `test(js): migrate websocket client protocol helper to ESM`
- `test(js): enforce ESM-only JavaScript files`
