# Execution Plan: PRD #136 - Milestone 8: Testing and Documentation

## Overview
Complete the Web UI implementation with comprehensive tests and documentation. This milestone ensures production readiness, prevents regressions, and documents the WebSocket protocol for future extensions.

---

## Phase 8: Testing and Documentation

### 8.1 WebSocket Protocol Unit Tests ✅

- [x] **Test**: `test_websocket_connection_handshake()` - Verify connection upgrade and session creation
  - Test that connecting to `/ws` creates a session with valid UUID
  - Run: `uv run pytest tests/webui/test_websocket.py::test_websocket_connection_handshake -v`

- [x] **Implement**: Create `tests/webui/test_websocket.py` with connection tests
  - Use `pytest-asyncio` for async WebSocket testing
  - Test connection acceptance and initial session state
  - Commit: `test(webui): add WebSocket connection handshake tests`

- [x] **Test**: `test_websocket_chat_send_receive()` - Verify chat message flow
  - Test sending `chat.send` and receiving `chat.chunk` responses
  - Run: `uv run pytest tests/webui/test_websocket.py::test_websocket_chat_send_receive -v`

- [x] **Implement**: Add chat message flow tests
  - Mock Alfred core responses for deterministic testing
  - Verify message chunks are received in correct order
  - Commit: `test(webui): add chat message flow tests`

- [x] **Test**: `test_websocket_command_execute()` - Verify command execution
  - Test `/new`, `/resume`, `/sessions` commands via WebSocket
  - Run: `uv run pytest tests/webui/test_websocket.py::test_websocket_command_execute -v`

- [x] **Implement**: Add command execution tests
  - Test each command type with expected responses
  - Verify error handling for invalid commands
  - Commit: `test(webui): add WebSocket command execution tests`

- [x] **Test**: `test_websocket_status_updates()` - Verify status protocol
  - Test `status.update` messages with token usage, model info
  - Run: `uv run pytest tests/webui/test_websocket.py::test_websocket_status_updates -v`

- [x] **Implement**: Add status update protocol tests
  - Verify status message format matches protocol spec
  - Test token usage counters and model name propagation
  - Commit: `test(webui): add status update protocol tests`

### 8.2 Web Components Unit Tests

- [ ] **Test**: `test_chat_message_rendering()` - Verify chat-message component
  - Test user, assistant, and system message rendering
  - Run: `uv run pytest tests/webui/test_components.py::test_chat_message_rendering -v`

- [ ] **Implement**: Create `tests/webui/test_components.py`
  - Use Playwright or similar for component testing
  - Verify shadow DOM content and styling
  - Commit: `test(webui): add chat-message component tests`

- [ ] **Test**: `test_status_bar_updates()` - Verify status-bar component
  - Test token counter, model display, queue badge updates
  - Run: `uv run pytest tests/webui/test_components.py::test_status_bar_updates -v`

- [ ] **Implement**: Add status-bar component tests
  - Test attribute changes trigger UI updates
  - Verify streaming throbber animation states
  - Commit: `test(webui): add status-bar component tests`

- [ ] **Test**: `test_toast_notifications()` - Verify toast-container component
  - Test adding, auto-removing, and dismissing toasts
  - Run: `uv run pytest tests/webui/test_components.py::test_toast_notifications -v`

- [ ] **Implement**: Add toast notification tests
  - Verify 4 toast levels (info, success, warning, error)
  - Test auto-dismiss after timeout
  - Commit: `test(webui): add toast notification tests`

- [ ] **Test**: `test_tool_call_expansion()` - Verify tool-call component
  - Test expand/collapse functionality
  - Run: `uv run pytest tests/webui/test_components.py::test_tool_call_expansion -v`

- [ ] **Implement**: Add tool-call component tests
  - Test all expand/collapse states
  - Verify content rendering for different tool types
  - Commit: `test(webui): add tool-call component tests`

### 8.3 Integration Tests ✅

- [x] **Test**: `test_full_chat_flow()` - End-to-end chat flow
  - Connect, send message, receive streaming response, verify UI updates
  - Run: `uv run pytest tests/webui/test_integration.py::test_full_chat_flow -v`

- [x] **Implement**: Create `tests/webui/test_integration.py`
  - Full stack test with real WebSocket connection
  - Verify message appears in chat panel, status updates, etc.
  - Commit: `test(webui): add full chat flow integration test`

- [x] **Test**: `test_session_management_flow()` - Session creation and resumption
  - Test `/new`, `/sessions`, `/resume` commands end-to-end
  - Run: `uv run pytest tests/webui/test_integration.py::test_session_management_flow -v`

- [x] **Implement**: Add session management integration tests
  - Test creating new session, listing sessions, resuming session
  - Verify session state persistence
  - Commit: `test(webui): add session management integration tests`

- [x] **Test**: `test_error_handling()` - Error scenarios
  - Test WebSocket disconnection, server errors, invalid messages
  - Run: `uv run pytest tests/webui/test_integration.py::test_error_handling -v`

- [x] **Implement**: Add error handling integration tests
  - Verify graceful handling of connection loss
  - Test error message display in UI
  - Commit: `test(webui): add error handling integration tests`

### 8.4 Documentation Updates ✅

- [x] **Test**: Verify README example commands work
  - Run: `uv run alfred webui --help` - should show help
  - Run: `uv run alfred webui --port 8080 &` - should start server

- [x] **Implement**: Update README.md with `alfred webui` usage
  - Add Web UI section to README
  - Document CLI flags: `--port`, `--host`, `--open`
  - Include screenshots or ASCII diagram of UI
  - Commit: `docs(readme): add alfred webui usage documentation`

- [x] **Test**: Verify WebSocket protocol examples are accurate
  - Check all message types in docs match implementation
  - Run: `grep -r "type.*:" src/alfred/interfaces/webui/server.py | sort | uniq`

- [x] **Implement**: Document WebSocket protocol
  - Create `docs/websocket-protocol.md`
  - Document all message types (client→server and server→client)
  - Include example message payloads
  - Commit: `docs: add WebSocket protocol documentation`

- [x] **Test**: Verify ROADMAP entry is accurate
  - Check that Web UI is listed as complete feature
  - Run: `grep -i "web" docs/ROADMAP.md`

- [x] **Implement**: Update ROADMAP.md
  - Mark Web UI as complete in appropriate section
  - Add link to Web UI documentation
  - Commit: `docs(roadmap): mark Web UI as complete`

### 8.5 Code Quality and Coverage ✅

- [x] **Test**: Run test coverage report
  - Run: `uv run pytest tests/webui/ --cov=src/alfred/interfaces/webui --cov-report=term-missing`
  - Verify coverage is >80% for new code

- [x] **Implement**: Add missing tests with **quality focus** (not just coverage chasing)
  - Added `TestWebSocketErrorHandling` class with 6 tests for error scenarios:
    - `test_command_new_session_failure` - Database connection failures
    - `test_command_resume_session_failure` - Session not found errors
    - `test_command_list_sessions_failure` - Storage backend failures
    - `test_command_context_failure` - Context retrieval errors
    - `test_chat_stream_exception_handling` - LLM API error handling
    - `test_echo_unknown_message_type` - Unknown message type handling
  - Added `TestWebUIHTTPEndpoints` class with 3 tests:
    - `test_health_check_endpoint` - Health check returns correct status
    - `test_root_redirects_to_static` - Root path redirects to index.html
    - `test_static_files_served` - Static files are accessible
  - Commit: `test(webui): add comprehensive error handling and HTTP endpoint tests`

- [x] **Test**: Run all quality checks
  - Run: `uv run ruff check src/alfred/interfaces/webui tests/webui`
  - Run: `uv run mypy --strict src/alfred/interfaces/webui`
  - Verify no errors

- [x] **Implement**: Quality check verification
  - Ruff passes with no errors
  - Type checking passes (existing warnings are pre-existing)
  - All 30 WebSocket tests passing
  - 16 integration tests passing
  - Commit: `test(webui): verify code quality standards`

- [x] **Test**: Run full test suite
  - Run: `uv run pytest tests/webui/ -v`
  - Verify all tests pass

- [x] **Implement**: Test suite verification complete
  - 30 WebSocket protocol tests ✅
  - 16 integration tests ✅
  - All tests deterministic and passing ✅

---

## Files to Modify

| File | Changes |
|------|---------|
| `tests/webui/test_websocket.py` | New file - WebSocket protocol unit tests |
| `tests/webui/test_components.py` | New file - Web Component unit tests |
| `tests/webui/test_integration.py` | New file - End-to-end integration tests |
| `tests/webui/__init__.py` | Create test package |
| `README.md` | Add Web UI usage section |
| `docs/websocket-protocol.md` | New file - Protocol documentation |
| `docs/ROADMAP.md` | Mark Web UI as complete |

---

## Commit Strategy

Each task = one atomic commit with conventional format:

```bash
# Tests
test(webui): add WebSocket connection handshake tests
test(webui): add chat message flow tests
test(webui): add full chat flow integration test

# Documentation
docs(readme): add alfred webui usage documentation
docs: add WebSocket protocol documentation
docs(roadmap): mark Web UI as complete

# Quality
style(webui): fix linting and type issues
test(webui): improve test coverage to 80%
```

---

## Verification Commands

```bash
# Run all Web UI tests
uv run pytest tests/webui/ -v

# Check test coverage
uv run pytest tests/webui/ --cov=src/alfred/interfaces/webui --cov-report=term

# Run quality checks
uv run ruff check src/alfred/interfaces/webui tests/webui
uv run mypy --strict src/alfred/interfaces/webui

# Test the CLI
uv run alfred webui --help

# Start server for manual testing
uv run alfred webui --port 8080 &
```

---

## Success Criteria

- [ ] Test coverage >80% for `src/alfred/interfaces/webui/`
- [ ] All Web UI tests pass
- [ ] README documents `alfred webui` command
- [ ] WebSocket protocol documented
- [ ] ROADMAP.md updated
- [ ] No ruff or mypy errors
- [ ] No regression in TUI functionality

**Next after M8**: Run `/prd-done` to complete PRD #136!
