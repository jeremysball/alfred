# Execution Plan: PRD #156 - Playwright Browser Control

## Overview

Session-scoped browser automation with Playwright. Tools are stateless; session manager holds browser instances. Screenshots stream to WebSocket connections per session.

---

## Phase 1: Browser Pool Infrastructure

### BrowserPool Class

- [ ] Test: `test_browser_pool_create_initializes_browser()` - verify pool creates browser with correct TTL
- [ ] Implement: `BrowserPool.create()` class method and `__init__`
- [ ] Run: `uv run pytest tests/tools/test_browser_pool.py::test_browser_pool_create_initializes_browser -v`

- [ ] Test: `test_browser_pool_page_returns_initialized_page()` - verify `page` property returns Page
- [ ] Implement: `_initialize()` and `page` property
- [ ] Run: `uv run pytest tests/tools/test_browser_pool.py::test_browser_pool_page_returns_initialized_page -v`

- [ ] Test: `test_browser_pool_is_expired_returns_true_after_ttl()` - verify TTL expiry detection
- [ ] Implement: `is_expired()` method
- [ ] Run: `uv run pytest tests/tools/test_browser_pool.py::test_browser_pool_is_expired_returns_true_after_ttl -v`

- [ ] Test: `test_browser_pool_close_cleans_up_resources()` - verify browser closes properly
- [ ] Implement: `close()` method
- [ ] Run: `uv run pytest tests/tools/test_browser_pool.py::test_browser_pool_close_cleans_up_resources -v`

- [ ] Test: `test_browser_pool_handles_import_error()` - verify graceful degradation when Playwright not installed
- [ ] Implement: Import error handling in `_initialize()`
- [ ] Run: `uv run pytest tests/tools/test_browser_pool.py::test_browser_pool_handles_import_error -v`

### Session Manager Extension

- [ ] Test: `test_session_manager_get_or_create_browser_creates_new()` - verify browser creation
- [ ] Implement: `get_or_create_browser()` method in SessionManager
- [ ] Run: `uv run pytest tests/core/test_session_manager.py::test_session_manager_get_or_create_browser_creates_new -v`

- [ ] Test: `test_session_manager_get_or_create_browser_reuses_existing()` - verify same browser returned
- [ ] Implement: Reuse logic for non-expired browsers
- [ ] Run: `uv run pytest tests/core/test_session_manager.py::test_session_manager_get_or_create_browser_reuses_existing -v`

- [ ] Test: `test_session_manager_get_or_create_browser_replaces_expired()` - verify expired browser replaced
- [ ] Implement: Expiry check and recreation
- [ ] Run: `uv run pytest tests/core/test_session_manager.py::test_session_manager_get_or_create_browser_replaces_expired -v`

- [ ] Test: `test_session_manager_close_browser_closes_and_removes()` - verify cleanup
- [ ] Implement: `close_browser()` method
- [ ] Run: `uv run pytest tests/core/test_session_manager.py::test_session_manager_close_browser_closes_and_removes -v`

- [ ] Test: `test_session_manager_close_session_closes_browser()` - verify session cleanup includes browser
- [ ] Implement: Call `close_browser()` from `close_session()`
- [ ] Run: `uv run pytest tests/core/test_session_manager.py::test_session_manager_close_session_closes_browser -v`

---

## Phase 2: Browser Control Tools

### BrowserTool

- [ ] Test: `test_browser_tool_goto_navigates_and_returns_title()` - verify goto action
- [ ] Implement: `execute()` with `goto` action using session manager
- [ ] Run: `uv run pytest tests/tools/test_browser.py::test_browser_tool_goto_navigates_and_returns_title -v`

- [ ] Test: `test_browser_tool_goto_accepts_ttl_parameter()` - verify TTL passed to session manager
- [ ] Implement: Extract and pass `ttl_seconds` param
- [ ] Run: `uv run pytest tests/tools/test_browser.py::test_browser_tool_goto_accepts_ttl_parameter -v`

- [ ] Test: `test_browser_tool_click_clicks_element()` - verify click action
- [ ] Implement: `click` action
- [ ] Run: `uv run pytest tests/tools/test_browser.py::test_browser_tool_click_clicks_element -v`

- [ ] Test: `test_browser_tool_fill_fills_input()` - verify fill action
- [ ] Implement: `fill` action
- [ ] Run: `uv run pytest tests/tools/test_browser.py::test_browser_tool_fill_fills_input -v`

- [ ] Test: `test_browser_tool_extract_returns_text()` - verify extract action
- [ ] Implement: `extract` action
- [ ] Run: `uv run pytest tests/tools/test_browser.py::test_browser_tool_extract_returns_text -v`

- [ ] Test: `test_browser_tool_close_closes_browser()` - verify close action delegates to session manager
- [ ] Implement: `close` action
- [ ] Run: `uv run pytest tests/tools/test_browser.py::test_browser_tool_close_closes_browser -v`

- [ ] Test: `test_browser_tool_returns_error_on_timeout()` - verify timeout handling
- [ ] Implement: Try/except for TimeoutError
- [ ] Run: `uv run pytest tests/tools/test_browser.py::test_browser_tool_returns_error_on_timeout -v`

- [ ] Test: `test_browser_tool_returns_error_on_unknown_action()` - verify unknown action handling
- [ ] Implement: Default case for unknown actions
- [ ] Run: `uv run pytest tests/tools/test_browser.py::test_browser_tool_returns_error_on_unknown_action -v`

- [ ] Test: `test_browser_tool_is_stateless()` - verify tool doesn't store browser reference
- [ ] Verify: Tool calls session manager on each execute, no instance variables
- [ ] Run: `uv run pytest tests/tools/test_browser.py::test_browser_tool_is_stateless -v`

### Tool Registration

- [ ] Test: `test_browser_tool_registered_in_registry()` - verify tool is discoverable
- [ ] Implement: Add `BrowserTool` to tool registry
- [ ] Run: `uv run pytest tests/tools/test_registry.py::test_browser_tool_registered_in_registry -v`

---

## Phase 3: Real-Time Preview (Web UI)

### Screenshot Streaming

- [ ] Test: `test_stream_manager_start_stream_creates_task()` - verify streaming starts
- [ ] Implement: `BrowserStreamManager.__init__()` and `start_stream()`
- [ ] Run: `uv run pytest tests/tools/test_browser_stream.py::test_stream_manager_start_stream_creates_task -v`

- [ ] Test: `test_stream_manager_screenshots_broadcast_to_session()` - verify `_broadcast_to_session` called
- [ ] Implement: `_stream_loop()` with screenshot capture and broadcast
- [ ] Run: `uv run pytest tests/tools/test_browser_stream.py::test_stream_manager_screenshots_broadcast_to_session -v`

- [ ] Test: `test_stream_manager_only_broadcasts_changed_screenshots()` - verify deduplication
- [ ] Implement: Compare with `_last_screenshot` before broadcast
- [ ] Run: `uv run pytest tests/tools/test_browser_stream.py::test_stream_manager_only_broadcasts_changed_screenshots -v`

- [ ] Test: `test_stream_manager_stop_stream_cancels_task()` - verify cleanup
- [ ] Implement: `stop_stream()` method
- [ ] Run: `uv run pytest tests/tools/test_browser_stream.py::test_stream_manager_stop_stream_cancels_task -v`

- [ ] Test: `test_stream_manager_handles_errors_gracefully()` - verify error handling stops stream
- [ ] Implement: Try/except in `_stream_loop()`
- [ ] Run: `uv run pytest tests/tools/test_browser_stream.py::test_stream_manager_handles_errors_gracefully -v`

### WebSocket Server Extension

- [ ] Test: `test_broadcast_to_session_sends_to_matching_connections()` - verify session filtering
- [ ] Implement: `_broadcast_to_session()` helper in server.py
- [ ] Run: `uv run pytest tests/interfaces/webui/test_server.py::test_broadcast_to_session_sends_to_matching_connections -v`

- [ ] Test: `test_connection_tracks_session_id()` - verify WebSocket connection knows its session
- [ ] Implement: Track session_id on WebSocket connection state
- [ ] Run: `uv run pytest tests/interfaces/webui/test_server.py::test_connection_tracks_session_id -v`

### Web UI Component

- [ ] Test: Manually verify browser preview component loads in UI
- [ ] Implement: `browser-preview.js` component with hex-to-image conversion
- [ ] Verify: Open Web UI, check browser preview element exists

- [ ] Test: Manually verify screenshot displays in preview panel
- [ ] Implement: Update `index.html` to include browser preview panel
- [ ] Verify: Trigger browser action, see screenshot appear

- [ ] Test: Manually verify URL display updates
- [ ] Implement: URL display element update logic
- [ ] Verify: Navigate to URL, see URL text update

---

## Phase 4: Agent Integration

### Tool Schema & Prompting

- [ ] Test: `test_browser_tool_schema_includes_all_actions()` - verify JSON schema complete
- [ ] Verify: Run `BrowserTool().get_schema()` and check actions documented
- [ ] Run: `uv run pytest tests/tools/test_browser.py::test_browser_tool_schema_includes_all_actions -v`

- [ ] Test: Manually verify LLM can understand browser tool
- [ ] Implement: Add TOOLS.md entry with usage examples
- [ ] Verify: Ask agent to "go to example.com" and confirm it plans browser actions

- [ ] Test: Manually verify error feedback to LLM
- [ ] Implement: Ensure error messages are descriptive for LLM
- [ ] Verify: Trigger timeout error, confirm agent receives clear message

### End-to-End Validation

- [ ] Test: Manually verify complete workflow
- [ ] Steps:
  1. Start Alfred Web UI
  2. Send message: "Go to httpbin.org and tell me the page title"
  3. Verify agent uses browser_control tool
  4. Verify screenshot streams to UI
  5. Verify agent reports correct title
- [ ] Mark complete when all steps pass

---

## Files to Create/Modify

### New Files
1. `src/alfred/tools/browser_pool.py` - BrowserPool class
2. `src/alfred/tools/browser.py` - BrowserTool class
3. `src/alfred/tools/browser_stream.py` - BrowserStreamManager class
4. `src/alfred/interfaces/webui/static/js/browser-preview.js` - Web UI component
5. `tests/tools/test_browser_pool.py` - BrowserPool tests
6. `tests/tools/test_browser.py` - BrowserTool tests
7. `tests/tools/test_browser_stream.py` - StreamManager tests

### Modified Files
1. `src/alfred/core/sessions.py` - Add browser methods to SessionManager
2. `src/alfred/interfaces/webui/server.py` - Add `_broadcast_to_session()` and session tracking
3. `src/alfred/interfaces/webui/static/index.html` - Add browser preview panel
4. `src/alfred/tools/__init__.py` or registry - Register BrowserTool
5. `data/TOOLS.md` - Document browser tool usage

### Dependencies
Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
browser = ["playwright>=1.40.0"]
```

---

## Commit Strategy

Each checkbox = one atomic commit:

```
feat(browser): add BrowserPool with TTL management
feat(browser): add session manager browser methods  
feat(browser): add stateless BrowserTool
test(browser): add BrowserPool tests
test(browser): add BrowserTool tests
feat(webui): add _broadcast_to_session for per-session screenshots
feat(webui): add browser preview component
feat(tools): register BrowserTool in registry
docs(tools): add browser tool documentation
```

---

## Verification Commands

```bash
# Run all browser-related tests
uv run pytest tests/tools/test_browser*.py -v

# Run with Playwright installed
uv run pytest tests/tools/test_browser*.py -v --browser

# Run full test suite (quick)
uv run pytest -m "not slow" -x

# Run full test suite (complete)
uv run pytest

# Manual verification: Start Alfred Web UI
uv run alfred --webui
```

---

## Progress Tracking

- [ ] Phase 1 Complete: BrowserPool + Session Manager
- [ ] Phase 2 Complete: BrowserTool + Registration  
- [ ] Phase 3 Complete: Streaming + Web UI
- [ ] Phase 4 Complete: Agent Integration + E2E

**Current Phase:** Phase 1
**Next Task:** Create `test_browser_pool_create_initializes_browser`
