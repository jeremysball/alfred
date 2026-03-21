# Execution Plan: PRD #136 - Web UI Milestone 2: Message Streaming

## Overview
Implement bidirectional message streaming between the Web UI and Alfred's LLM backend. This phase establishes the WebSocket protocol for chat messages and integrates with Alfred's `chat_stream()` method.

---

## Milestone 2: Message Streaming

### WebSocket Protocol Implementation

- [x] Test: `test_chat_send_message()` - Verify client can send chat message
- [x] Implement: Add `chat.send` message handler in WebSocket endpoint
- [x] Run: `uv run pytest tests/webui/test_protocol.py -v` (12 tests passing)

- [x] Test: `test_chat_chunk_received()` - Verify server streams chunks to client
- [x] Implement: Add `chat.chunk` message type for streaming tokens
- [x] Run: `uv run pytest tests/webui/test_protocol.py -v`

- [x] Test: `test_chat_complete_received()` - Verify completion message sent
- [x] Implement: Add `chat.complete` message with final content and usage
- [x] Run: `uv run pytest tests/webui/test_protocol.py -v`

- [x] Test: `test_chat_error_handling()` - Verify errors are properly communicated
- [x] Implement: Add `chat.error` message type for error handling
- [x] Run: `uv run pytest tests/webui/test_protocol.py -v`

### Alfred Integration

- [x] Test: `test_chat_stream_integration()` - Verify integration with Alfred.chat_stream()
- [x] Implement: Wire WebSocket handler to Alfred's chat_stream() method
- [x] Run: `uv run pytest tests/webui/test_chat.py::test_chat_stream_integration -v`

- [x] Test: `test_message_persistence()` - Verify messages are saved to session
- [x] Implement: Ensure chat messages persist to Alfred's session storage
- [x] Run: `uv run pytest tests/webui/test_chat.py::test_message_persistence -v`

### Frontend Components

- [x] Test: `test_chat_message_component()` - Verify chat-message Web Component renders
- [x] Implement: Create `<chat-message>` Web Component in static/js/components/
- [x] Run: `uv run pytest tests/webui/test_frontend.py -v` (7 tests passing)

- [x] Test: `test_message_display()` - Verify messages appear in chat panel
- [x] Implement: Add chat panel with message display to index.html
- [x] Run: `uv run pytest tests/webui/test_frontend.py::test_index_html_has_chat_ui -v`

- [x] Test: `test_auto_scroll()` - Verify auto-scroll to newest message
- [x] Implement: Add auto-scroll behavior to chat panel
- [x] Run: Manual verification - browser check

- [x] Test: `test_connection_status()` - Verify connection status indicator
- [x] Implement: Add connection status component (connected/disconnected)
- [x] Run: `uv run pytest tests/webui/test_frontend.py::test_chat_styles_exist -v`

### Protocol Definition

- [x] Test: `test_protocol_types()` - Verify protocol message types are defined
- [x] Implement: Create protocol.py with TypeScript-compatible type definitions
- [x] Run: `uv run pytest tests/webui/test_protocol.py -v` (12 tests passing)

- [x] Test: `test_message_validation()` - Verify message validation works
- [x] Implement: Add Pydantic models for WebSocket message validation
- [x] Run: `uv run pytest tests/webui/test_validation.py -v` (29 tests passing)

---

## Files to Modify/Created

### New Files
1. `src/alfred/interfaces/webui/protocol.py` - WebSocket protocol definitions
2. `src/alfred/interfaces/webui/static/js/components/chat-message.js` - Chat message component
3. `src/alfred/interfaces/webui/static/js/websocket-client.js` - WebSocket client
4. `tests/webui/test_chat.py` - Chat integration tests
5. `tests/webui/test_protocol.py` - Protocol tests

### Modified Files
1. `src/alfred/interfaces/webui/server.py` - Add chat message handlers
2. `src/alfred/interfaces/webui/static/index.html` - Add chat panel
3. `src/alfred/interfaces/webui/static/js/main.js` - Initialize chat components
4. `src/alfred/interfaces/webui/static/css/base.css` - Add chat styling

---

## Progress Summary

### ✅ Completed (12/12 tasks) - MILESTONE 2 COMPLETE!
- ✅ WebSocket Protocol Definitions (4/4 tasks)
- ✅ Alfred Integration (2/2 tasks)
- ✅ Frontend Components (4/4 tasks)
- ✅ Protocol Validation (2/2 tasks)

---

## Verification Commands

### Quick Test
```bash
# Start server in background
uv run alfred webui --port 8080 &
SERVER_PID=$!
sleep 2

# Run all WebSocket tests
uv run pytest tests/webui/test_websocket.py -v

# Run chat integration tests
uv run pytest tests/webui/test_chat.py -v

# Stop server
kill $SERVER_PID
```

### Full Test Suite
```bash
# All WebUI tests
uv run pytest tests/webui/ -v
```

### Manual Testing
```bash
# Start server
uv run alfred webui --port 8080

# Open browser
# 1. Navigate to http://localhost:8080
# 2. Open browser console
# 3. Type message in input and send
# 4. Verify streaming response appears
# 5. Check WebSocket messages in Network tab
```

---

## Dependencies

```toml
# Already added in Milestone 1:
# - fastapi
# - uvicorn[standard]
# - websockets

# May need for validation:
pydantic = ">=2.0.0"
```

---

## Commit Strategy

```bash
# Example commit sequence:
git commit -m "feat(webui): add WebSocket protocol definitions"
git commit -m "feat(webui): implement chat.send message handler"
git commit -m "feat(webui): add chat.chunk streaming support"
git commit -m "feat(webui): integrate with Alfred chat_stream()"
git commit -m "feat(webui): add chat-message Web Component"
git commit -m "feat(webui): implement auto-scroll behavior"
git commit -m "feat(webui): add connection status indicator"
git commit -m "test(webui): add chat integration tests"
```

---

## Success Criteria

Before marking Milestone 2 complete:

- [x] User can type message and receive streaming response
- [x] Messages appear in correct order
- [x] Streaming is smooth (no jank)
- [x] Connection loss is detected and shown
- [x] All 12 tasks complete with 77 tests passing
- [x] Manual testing confirms end-to-end functionality

## Completion Summary

### Test Coverage
| Component | Tests | Status |
|-----------|-------|--------|
| Server (M1) | 20 | ✅ Passing |
| Protocol (M2) | 12 | ✅ Passing |
| Chat Integration (M2) | 9 | ✅ Passing |
| Frontend (M2) | 7 | ✅ Passing |
| Validation (M2) | 29 | ✅ Passing |
| **Total** | **77** | ✅ **All Passing** |

### New Files Created
- `src/alfred/interfaces/webui/validation.py` - Pydantic models + validation
- `tests/webui/test_validation.py` - 29 validation tests

### Key Features Implemented
- **Pydantic Models**: Type-safe message validation for all protocol types
- **Validation Function**: `validate_client_message()` returns (is_valid, message, error)
- **CamelCase Support**: Models use `populate_by_name` for JSON compatibility
- **Error Handling**: Detailed validation error messages
- **Comprehensive Tests**: 29 tests covering valid/invalid scenarios
