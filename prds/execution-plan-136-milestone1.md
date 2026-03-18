# Execution Plan: PRD #136 - Web UI Milestone 1: Foundation

## Overview
Create the foundational WebSocket server infrastructure for Alfred's Web UI. This phase establishes the FastAPI application, WebSocket endpoint, static file serving, CLI command integration, and graceful shutdown handling.

---

## Phase 1: Foundation

### FastAPI Application Structure

- [x] Test: `test_webui_module_exists()` - Verify webui module is importable
- [x] Implement: Create `src/alfred/interfaces/webui/__init__.py` with module exports
- [x] Run: `uv run python -c "from alfred.interfaces.webui import WebUIServer; print('OK')"`

- [x] Test: `test_fastapi_app_factory()` - Verify FastAPI app can be created
- [x] Implement: Create `src/alfred/interfaces/webui/server.py` with `create_app()` factory
- [x] Run: `uv run pytest tests/webui/test_server.py::test_fastapi_app_factory -v`

### WebSocket Endpoint

- [x] Test: `test_websocket_endpoint_exists()` - WebSocket route accepts connections
- [x] Implement: Add `/ws` WebSocket endpoint with connection accept/reject logic
- [x] Run: `uv run pytest tests/webui/test_websocket.py::test_websocket_endpoint_exists -v`

- [x] Test: `test_websocket_echo_message()` - Connected client can send/receive messages
- [x] Implement: Basic message echo handler for testing connectivity
- [x] Run: `uv run pytest tests/webui/test_websocket.py::test_websocket_echo_message -v`

- [x] Test: `test_websocket_multiple_clients()` - Server handles multiple concurrent connections
- [x] Implement: Connection manager to track active WebSocket connections
- [x] Run: `uv run pytest tests/webui/test_websocket.py::test_websocket_multiple_clients -v`

### Static File Serving

- [x] Test: `test_static_directory_exists()` - Static files directory is created
- [x] Implement: Create `src/alfred/interfaces/webui/static/` directory structure
- [x] Run: `uv run python -c "from pathlib import Path; assert Path('src/alfred/interfaces/webui/static').exists(); print('OK')"`

- [x] Test: `test_index_html_served()` - Root path serves HTML entry point
- [x] Implement: Create `static/index.html` and mount static files in FastAPI
- [x] Run: `uv run pytest tests/webui/test_static.py::test_index_html_served -v`

- [x] Test: `test_static_js_files_served()` - JavaScript files are accessible
- [x] Implement: Create `static/js/` directory and verify file serving
- [x] Run: `uv run pytest tests/webui/test_static.py::test_static_js_files_served -v`

- [x] Test: `test_static_css_files_served()` - CSS files are accessible
- [x] Implement: Create `static/css/` directory and verify file serving
- [x] Run: `uv run pytest tests/webui/test_static.py::test_static_css_files_served -v`

### Health Check Endpoint

- [x] Test: `test_health_endpoint_returns_ok()` - `/health` returns 200 with status
- [x] Implement: Add `/health` endpoint returning `{"status": "ok"}`
- [x] Run: `uv run pytest tests/webui/test_server.py::test_health_endpoint_returns_ok -v`

- [ ] Test: `test_health_includes_version()` - Health check includes app version
- [ ] Implement: Add version field to health response
- [ ] Run: `uv run pytest tests/webui/test_server.py::test_health_includes_version -v`

### CLI Command Integration

- [ ] Test: `test_webui_command_registered()` - `alfred webui` command exists
- [ ] Implement: Add `webui` subcommand to `src/alfred/cli/main.py`
- [ ] Run: `uv run alfred webui --help` shows help message

- [ ] Test: `test_webui_command_accepts_port()` - `--port` flag is recognized
- [ ] Implement: Add `--port` option with default 8080
- [ ] Run: `uv run pytest tests/webui/test_cli.py::test_webui_command_accepts_port -v`

- [ ] Test: `test_webui_command_accepts_open()` - `--open` flag is recognized
- [ ] Implement: Add `--open` boolean flag to launch browser
- [ ] Run: `uv run pytest tests/webui/test_cli.py::test_webui_command_accepts_open -v`

- [ ] Test: `test_webui_server_starts_on_specified_port()` - Server actually starts
- [ ] Implement: Wire CLI command to start FastAPI server with uvicorn
- [ ] Run: `timeout 3 uv run alfred webui --port 9999 || true` (verify it starts)

### Graceful Shutdown

- [ ] Test: `test_server_shuts_down_on_sigint()` - Ctrl+C stops server cleanly
- [ ] Implement: Signal handler for graceful shutdown
- [ ] Run: `uv run pytest tests/webui/test_server.py::test_server_shuts_down_on_sigint -v`

- [ ] Test: `test_websocket_connections_closed_on_shutdown()` - Active connections closed cleanly
- [ ] Implement: Close all WebSocket connections before exiting
- [ ] Run: `uv run pytest tests/webui/test_websocket.py::test_websocket_connections_closed_on_shutdown -v`

---

## Files to Modify/Created

### New Files
1. `src/alfred/interfaces/webui/__init__.py` - Module exports
2. `src/alfred/interfaces/webui/server.py` - FastAPI app and WebSocket handler
3. `src/alfred/interfaces/webui/static/index.html` - HTML entry point
4. `src/alfred/interfaces/webui/static/css/base.css` - Base styles
5. `src/alfred/interfaces/webui/static/js/main.js` - Frontend entry point
6. `tests/webui/__init__.py` - Test module
7. `tests/webui/test_server.py` - Server tests
8. `tests/webui/test_websocket.py` - WebSocket tests
9. `tests/webui/test_static.py` - Static file tests
10. `tests/webui/test_cli.py` - CLI command tests

### Modified Files
1. `src/alfred/cli/main.py` - Add `webui` subcommand
2. `pyproject.toml` - Add FastAPI/uvicorn dependencies if needed

---

## Dependencies to Add

```toml
# In pyproject.toml [project.dependencies]
fastapi = ">=0.110.0"
uvicorn = { extras = ["standard"], version = ">=0.29.0" }
websockets = ">=12.0"  # For WebSocket support
```

---

## Commit Strategy

Each checkbox above = one atomic commit:

```bash
# Example commit sequence:
git commit -m "feat(webui): create webui module structure"
git commit -m "feat(webui): add FastAPI app factory"
git commit -m "feat(webui): implement WebSocket endpoint"
git commit -m "test(webui): verify WebSocket echo functionality"
git commit -m "feat(webui): add static file serving"
git commit -m "feat(webui): create HTML entry point"
git commit -m "feat(webui): add health check endpoint"
git commit -m "feat(cli): add webui subcommand with --port and --open flags"
git commit -m "feat(webui): implement graceful shutdown handling"
```

---

## Verification Commands

### Quick Health Check
```bash
# Start server in background
uv run alfred webui --port 8080 &
SERVER_PID=$!

# Wait for startup
sleep 2

# Test health endpoint
curl http://localhost:8080/health

# Test WebSocket (using websocat or similar)
echo '{"type":"test"}' | websocat ws://localhost:8080/ws

# Stop server
kill $SERVER_PID
```

### Full Test Suite
```bash
uv run pytest tests/webui/ -v
```

---

## Success Criteria

- [ ] `alfred webui --help` shows available options
- [ ] `alfred webui --port 8080` starts server on specified port
- [ ] Browser can connect to `ws://localhost:8080/ws`
- [ ] `curl http://localhost:8080/health` returns `{"status": "ok"}`
- [ ] Static files served at `http://localhost:8080/`
- [ ] Ctrl+C shuts down server cleanly
- [ ] All tests pass: `uv run pytest tests/webui/ -v`

---

## Progress Tracking

**Started**: 2026-03-18  
**Completed**: _Not started_  
**Current Task**: FastAPI Application Structure

### Completed Tasks
- [x] Module Initialization - WebUIServer class created with tests
- [x] FastAPI Application Structure - create_app() factory implemented and tested
- [x] WebSocket Endpoint - /ws endpoint with connection handling and tests

### In Progress
- [ ] Static File Serving

### Remaining
- [ ] WebSocket Endpoint
- [ ] Static File Serving
- [ ] Health Check Endpoint
- [ ] CLI Command Integration
- [ ] Graceful Shutdown
