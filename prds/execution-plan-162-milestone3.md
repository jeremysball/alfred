# Execution Plan: PRD #162 - Milestone 3: Message Sending and Reconnect Behavior

## Overview
Ensure messages continue to send correctly across disconnects and reconnects by making connection attempts idempotent, preventing listener leaks, and keeping queue flushing predictable.

---

## Phase 1: Idempotent connect()

### Connect State Guard

- [ ] Test: `test_connect_is_idempotent_when_open()` - verify connect() is a no-op when WebSocket is already OPEN
- [ ] Implement: Add guard at start of `connect()` to return early if `this.ws?.readyState === WebSocket.OPEN`
- [ ] Run: `uv run pytest tests/webui/test_websocket_client_protocol.py -v -k "idempotent"`

- [ ] Test: `test_connect_is_idempotent_when_connecting()` - verify connect() is a no-op when WebSocket is CONNECTING
- [ ] Implement: Add guard at start of `connect()` to return early if `this.ws?.readyState === WebSocket.CONNECTING`
- [ ] Run: `uv run pytest tests/webui/test_websocket_client_protocol.py -v -k "idempotent"`

- [ ] Test: `test_connect_is_idempotent_when_closing()` - verify connect() waits or returns early when WebSocket is CLOSING
- [ ] Implement: Add guard at start of `connect()` to return early if `this.ws?.readyState === WebSocket.CLOSING`
- [ ] Run: `uv run pytest tests/webui/test_websocket_client_protocol.py -v -k "idempotent"`

---

## Phase 2: Lifecycle Listener Cleanup

### Freeze/Resume Handler Deduplication

- [ ] Test: `test_no_duplicate_freeze_handlers()` - verify freeze/resume listeners aren't duplicated on reconnect
- [ ] Implement: Track if freeze/resume handlers are already registered; skip if present
- [ ] Run: `uv run pytest tests/webui/test_reconnect.py -v -k "duplicate"`

### Pagehide/Pageshow Handler Deduplication

- [ ] Test: `test_no_duplicate_pagehide_handlers()` - verify pagehide/pageshow listeners aren't duplicated on reconnect
- [ ] Implement: Track if pagehide/pageshow handlers are already registered; skip if present
- [ ] Run: `uv run pytest tests/webui/test_reconnect.py -v -k "duplicate"`

---

## Phase 3: Queue Flushing Behavior

### Queue Flush After Reconnect

- [ ] Test: `test_queue_flushes_after_reconnect()` - verify queued messages are sent after transient disconnect
- [ ] Implement: Ensure `_flushMessageQueue()` is called in `onopen` after reconnect
- [ ] Run: `uv run pytest tests/webui/test_reconnect.py -v -k "queue"`

### Composer State During Disconnect

- [ ] Test: `test_composer_not_wedged_during_disconnect()` - verify composer remains usable during transient disconnect
- [ ] Implement: Ensure input is not permanently disabled when connection drops
- [ ] Run: `uv run pytest tests/webui/test_reconnect.py -v -k "composer"`

---

## Files to Modify

1. `src/alfred/interfaces/webui/static/js/websocket-client.js`
   - Add idempotent guards to `connect()` method
   - Add listener tracking to prevent duplicates
   - Verify queue flush behavior

2. `tests/webui/test_websocket_client_protocol.py` (new or existing)
   - Add tests for connect() idempotency across all readyStates
   - Add tests for listener deduplication

3. `tests/webui/test_reconnect.py` (existing)
   - Add tests for queue flushing after reconnect
   - Add tests for composer state during disconnect

## Commit Strategy

Each checkbox = one atomic commit:
- `test(websocket): verify connect() idempotent when OPEN`
- `feat(websocket): guard connect() when already OPEN`
- `test(websocket): verify no duplicate freeze handlers`
- `fix(websocket): track freeze handler registration`
- etc.

## Verification Commands

```bash
# Run all WebSocket client tests
uv run pytest tests/webui/test_websocket_client_protocol.py -v

# Run reconnect tests
uv run pytest tests/webui/test_reconnect.py -v

# Run full Web UI test suite
uv run pytest tests/webui/ -v --timeout=60
```

---

## Progress Tracking

**Started**: 2026-03-27

**Completed**:
- [x] Phase 1: Idempotent connect() ✅
- [x] Phase 2: Lifecycle Listener Cleanup ✅
- [x] Phase 3: Queue Flushing Behavior ✅

**Current Task**: All phases complete - Milestone 3 finished
