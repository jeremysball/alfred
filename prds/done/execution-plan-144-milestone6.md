# Execution Plan: PRD #144 - Milestone 6

## Overview

Bring the Web UI server and browser-client diagnostics under the same surface model as the core runtime. The goal is that mixed core/Web UI debugging is immediately readable, with explicit `webui-server` and `webui-client` identity in both structured logs and browser console output.

**Current Phase:** Milestone 6 - Web UI server/client surface alignment

---

## Milestone 6: Web UI server/client surface alignment

### 6.1 Web UI server logs use the `webui-server` surface

- [ ] **Test**: `test_webui_server_logs_use_the_webui_server_surface()`
  - Extend `tests/webui/test_server.py` or create a focused `tests/webui/test_frontend_logging.py`
  - Exercise representative FastAPI server paths such as health/status hydration and websocket/session setup
  - Assert debug logs are tagged with `surface=webui-server` in file output and render with a stable `[webui-server]` prefix in console output where applicable
- [ ] **Implement**: align `src/alfred/interfaces/webui/server.py`
  - Route Web UI server diagnostics through the shared surface helpers
  - Keep server-side lifecycle logs distinct from core runtime logs
  - Preserve existing payload behavior while improving readability
- [ ] **Run**: `uv run pytest tests/webui/test_server.py -v`

### 6.2 Browser-client console logs use the `webui-client` surface

- [ ] **Test**: `test_webui_client_console_logs_are_prefixed_with_surface()`
  - Extend `tests/webui/test_frontend_logging.py`
  - Assert browser-side helpers such as `webui-client-logger.js`, `main.js`, `websocket-client.js`, and any related client helpers emit a stable `[webui-client]` prefix
  - Keep the check source-based so it stays fast and deterministic
- [ ] **Implement**: prefix browser console output with `[webui-client]`
  - Keep client diagnostics visually distinct from server logs
  - Avoid changing runtime behavior beyond log formatting and routing
- [ ] **Run**: `uv run pytest tests/webui/test_frontend_logging.py -v`

### 6.3 Mixed Web UI and core debugging stays unambiguous

- [ ] **Test**: `test_webui_and_core_logs_remain_visually_distinct()`
  - Extend or add a regression test that captures both core and Web UI log streams together
  - Assert the surfaces remain unambiguous in the same session
- [ ] **Implement**: clean up any shared logging helpers or call sites that still blur the surface boundary
  - Keep the taxonomy consistent across the runtime and Web UI layers
- [ ] **Run**: `uv run pytest tests/test_observability.py tests/test_cli_webui_logging.py tests/webui/test_frontend_logging.py -v`

---

## Files to Modify

1. `src/alfred/interfaces/webui/server.py` - Web UI server surface logging
2. `src/alfred/interfaces/webui/static/js/websocket-client.js` - browser client logging prefix and runtime diagnostics
3. `src/alfred/interfaces/webui/static/js/main.js` - browser client logging prefix and event plumbing
4. `src/alfred/interfaces/webui/static/js/webui-client-logger.js` - stable browser-client prefix wrapper
5. `tests/webui/test_server.py` - server surface regression coverage
6. `tests/webui/test_frontend_logging.py` - browser-client surface regression coverage
7. `tests/test_observability.py` - mixed-surface logging assertions

## Verification Commands

```bash
uv run pytest tests/webui/test_server.py tests/webui/test_frontend_logging.py tests/test_observability.py -q
uv run ruff check src/ tests/
uv run mypy --strict src/
uv run pytest -m "not slow"
uv run alfred webui --port 8080
```

## Commit Strategy

Suggested atomic commits:
- `test(webui): cover server surface logging`
- `fix(webui): tag server logs with webui-server`
- `test(webui): cover client surface logging`
- `fix(webui): prefix browser logs with webui-client`
- `test(observability): verify mixed surface readability`

## Next Task

- [ ] **Test**: `test_webui_server_logs_use_the_webui_server_surface()`
- [ ] **Implement**: align `src/alfred/interfaces/webui/server.py`
- [ ] **Run**: `uv run pytest tests/webui/test_server.py -v`
