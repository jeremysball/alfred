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

- [ ] Test: `test_chat_message_component()` - Verify chat-message Web Component renders
- [ ] Implement: Create `<chat-message>` Web Component in static/js/components/
- [ ] Run: `uv run pytest tests/webui/test_static.py::test_chat_message_component -v`

- [ ] Test: `test_message_display()` - Verify messages appear in chat panel
- [ ] Implement: Add chat panel with message display to index.html
- [ ] Run: Manual verification - browser check

- [ ] Test: `test_auto_scroll()` - Verify auto-scroll to newest message
- [ ] Implement: Add auto-scroll behavior to chat panel
- [ ] Run: Manual verification - browser check

- [ ] Test: `test_connection_status()` - Verify connection status indicator
- [ ] Implement: Add connection status component (connected/disconnected)
- [ ] Run: Manual verification - browser check

### Protocol Definition

- [ ] Test: `test_protocol_types()` - Verify protocol message types are defined
- [ ] Implement: Create protocol.py with TypeScript-compatible type definitions
- [ ] Run: `uv run pytest tests/webui/test_protocol.py::test_protocol_types -v`

- [ ] Test: `test_message_validation()` - Verify message validation works
- [ ] Implement: Add Pydantic models for WebSocket message validation
- [ ] Run: `uv run pytest tests/webui/test_protocol.py::test_message_validation -v`

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

### Completed (6/12 tasks)
- ✅ WebSocket Protocol Definitions (4/4 tasks)
- ✅ Alfred Integration (2/2 tasks)

### Remaining (6/12 tasks)
- ⏳ Frontend Components (0/4 tasks)
  - [ ] Create `<chat-message>` Web Component
  - [ ] Build chat panel with auto-scroll
  - [ ] Add connection status indicator
  - [ ] Update index.html with chat UI
- ⏳ Protocol Validation (0/2 tasks)
  - [ ] Add Pydantic models for message validation
  - [ ] Add validation tests

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

- [ ] User can type message and receive streaming response
- [ ] Messages appear in correct order
- [ ] Streaming is smooth (no jank)
- [ ] Connection loss is detected and shown
- [ ] All 12+ tests passing
- [ ] Manual testing confirms end-to-end functionality
