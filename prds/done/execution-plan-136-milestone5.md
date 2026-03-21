# Execution Plan: PRD #136 - Web UI Milestone 5: Session Management

## Overview
Implement full session command support for the Alfred Web UI.

---

## Milestone 5: Session Management

### /new Command

- [x] Test: `test_new_command_creates_session()` - Verify /new creates new session
- [x] Implement: Add /new command handler in WebSocket server
- [x] Run: `uv run pytest tests/webui/test_sessions.py::test_new_command -v`

### /resume Command

- [x] Test: `test_resume_command_loads_session()` - Verify /resume loads session history
- [x] Implement: Add /resume command with session loading
- [x] Run: `uv run pytest tests/webui/test_sessions.py::test_resume_command -v`

- [x] Test: `test_resume_synchronization()` - Verify session state sync on resume
- [x] Implement: Sync conversation history on session resume
- [x] Run: Manual verification - browser check

### /sessions Command

- [x] Test: `test_sessions_command_lists_sessions()` - Verify /sessions returns list
- [x] Implement: Add /sessions command handler
- [x] Run: `uv run pytest tests/webui/test_sessions.py::test_sessions_command -v`

- [x] Test: `test_sessions_metadata()` - Verify session metadata displayed correctly
- [x] Implement: Format session list with metadata
- [x] Run: Manual verification - browser check

### /session Command

- [x] Test: `test_session_command_shows_info()` - Verify /session shows current session
- [x] Implement: Add /session command for current session info
- [x] Run: `uv run pytest tests/webui/test_sessions.py::test_session_command -v`

### /context Command

- [x] Test: `test_context_command_shows_system()` - Verify /context shows system context
- [x] Implement: Add /context command handler
- [x] Run: `uv run pytest tests/webui/test_sessions.py::test_context_command -v`

### Session Loading Protocol

- [x] Test: `test_session_loaded_message()` - Verify session.loaded message structure
- [x] Implement: Add session.loaded WebSocket message type
- [x] Run: `uv run pytest tests/webui/test_protocol.py::test_session_loaded -v`

---

## Files to Modify/Created

### New Files
1. `tests/webui/test_sessions.py` - Session management tests

### Modified Files
1. `src/alfred/interfaces/webui/server.py` - Add command handlers
2. `src/alfred/interfaces/webui/static/js/main.js` - Handle session commands
3. `src/alfred/interfaces/webui/static/js/websocket-client.js` - Session protocol

---

## Commands to Implement

```
/new              - Start new session
/resume <id>      - Resume session (with ID or fuzzy search)
/sessions         - List recent sessions with metadata
/session          - Show current session ID and info
/context          - Show system context (cwd, files, etc.)
```

---

## Verification Commands

### Quick Test
```bash
# Run session tests
uv run pytest tests/webui/test_sessions.py -v

# Run all webui tests
uv run pytest tests/webui/ -v
```

### Manual Testing
```bash
# Start server
uv run alfred webui --port 8080

# Test checklist:
# 1. Type /new - should create new session
# 2. Send some messages
# 3. Type /sessions - should show session list
# 4. Type /session - should show current session info
# 5. Type /resume <id> - should load previous session
# 6. Type /context - should show system context
```

---

## Progress Summary

### ✅ Completed (7/7 tasks) - MILESTONE 5 COMPLETE!
- ✅ /new Command (1/1 tasks)
- ✅ /resume Command (2/2 tasks)
- ✅ /sessions Command (2/2 tasks)
- ✅ /session Command (1/1 tasks)
- ✅ /context Command (1/1 tasks)

---

## Success Criteria

Before marking Milestone 5 complete:

- [x] All session commands work via WebSocket
- [x] Session loading restores conversation history
- [x] Session list shows correct metadata
- [x] Context display matches TUI format
- [x] All tests passing (100 total)

---

## Completion Summary

### Test Coverage
| Component | Tests | Status |
|-----------|-------|--------|
| Server (M1) | 20 | ✅ Passing |
| Protocol (M2) | 12 | ✅ Passing |
| Chat Integration (M2) | 9 | ✅ Passing |
| Frontend (M2) | 7 | ✅ Passing |
| Validation (M2) | 29 | ✅ Passing |
| Tool Calls (M3) | 10 | ✅ Passing |
| Input System (M4) | 6 | ✅ Passing |
| Session Management (M5) | 7 | ✅ Passing |
| **Total** | **100** | ✅ **All Passing** |

### New Files Created
- `tests/webui/test_sessions.py` - 7 session management tests

### Key Features Implemented
- **Session Commands**: /new, /resume, /sessions, /session, /context
- **Session Protocol**: session.new, session.loaded, session.list, session.info, context.info
- **Session Loading**: Restores conversation history with message reconstruction
- **Frontend Handlers**: Display session info in system messages

## Dependencies

```toml
# Already available:
# - fastapi
# - websockets
# - pydantic
```

---

## Commit Strategy

```bash
git commit -m "feat(webui): implement /new command"
git commit -m "feat(webui): implement /resume command with session loading"
git commit -m "feat(webui): implement /sessions command"
git commit -m "feat(webui): implement /session command"
git commit -m "feat(webui): implement /context command"
git commit -m "feat(webui): add session.loaded protocol message"
git commit -m "test(webui): add session management tests"
```
