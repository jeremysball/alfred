# Execution Plan: PRD #162 - Milestone 4: Debug Instrumentation and Log Policy

## Overview
Make failures diagnosable without flooding the console by wiring the Web UI debug flag through CLI startup into browser/client config, distinguishing server logs from browser/client logs, and emitting structured summaries for connection lifecycle events.

---

## Phase 1: CLI Flag Plumbing ✅ COMPLETE

### WebUI Subcommand Debug Option

- [x] Test: `test_webui_log_debug_flag_accepted()` - verify `webui --log debug` is accepted by CLI
- [x] Implement: Add `--log` option to `webui_app` callback in `main.py`
- [x] Run: `uv run pytest tests/webui/test_webui_cli.py -v -k "log_debug"`

### WebUI Server Factory Passes Debug Flag

- [x] Test: `test_webui_server_receives_debug_flag()` - verify `_build_server_controller` receives debug parameter
- [x] Implement: Update `_build_server_controller` signature and pass `debug=True` when `--log debug` is set
- [x] Run: `uv run pytest tests/webui/test_webui_cli.py -v -k "server_receives"`

**Evidence**:
- Added `log` parameter with `typer.Option` to `webui_callback` in `main.py`
- Updated `_build_server_controller`, `run_webui_server`, `run_webui_hotswap` to accept `debug` parameter
- Created `tests/webui/test_webui_cli.py` with 2 tests covering CLI flag acceptance and server parameter passing

---

## Phase 2: Browser Config Verification ✅ COMPLETE

### App Config Includes Debug Flag

- [x] Test: `test_app_config_includes_debug_flag_when_false()` - verify `/app-config.js` returns `debug: false` when server created without debug
- [x] Test: `test_app_config_includes_debug_flag_when_true()` - verify `/app-config.js` returns `debug: true` when server created with debug
- [x] Verify: `_render_webui_config_script` already handles this, confirmed via tests
- [x] Run: `uv run pytest tests/webui/test_server_parity.py -v -k "app_config"`

### WebSocket Client Reads Debug Config

- [x] Test: `test_websocket_client_reads_debug_config()` - verify `WEBSOCKET_DEBUG_ENABLED` is set from window config
- [x] Verify: Current implementation already reads from `window.__ALFRED_WEBUI_CONFIG__`
- [x] Run: `uv run pytest tests/webui/test_websocket_client_protocol.py -v -k "debug_config"`

**Evidence**:
- Added 2 tests in `test_server_parity.py` verifying `/app-config.js` returns correct debug flag
- Added 1 test in `test_websocket_client_protocol.py` verifying WebSocket client reads debug config
- All tests pass - implementation already works correctly

---

## Phase 3: Structured Lifecycle Logging

### Connection Lifecycle Events

- [ ] Test: `test_debug_logs_connection_open()` - verify 'WebSocket connected' is prefixed in debug mode
- [ ] Implement: Add `[websocket]` prefix to connection logs when debug enabled
- [ ] Run: `uv run pytest tests/webui/test_frontend_logging.py -v -k "connection_open"`

- [ ] Test: `test_debug_logs_connection_close()` - verify close code/reason logged with prefix
- [ ] Implement: Log close events with `[websocket]` prefix including code and reason
- [ ] Run: `uv run pytest tests/webui/test_frontend_logging.py -v -k "connection_close"`

- [ ] Test: `test_debug_logs_reconnect_attempts()` - verify reconnect attempts logged with attempt count
- [ ] Implement: Log reconnect scheduling with `[websocket]` prefix
- [ ] Run: `uv run pytest tests/webui/test_frontend_logging.py -v -k "reconnect"`

### Ping/Pong Instrumentation

- [ ] Test: `test_debug_logs_ping_pong()` - verify ping/pong timing logged in debug mode
- [ ] Implement: Log ping sends and pong receives with latency calculation
- [ ] Run: `uv run pytest tests/webui/test_frontend_logging.py -v -k "ping_pong"`

### Queue Flush Instrumentation

- [ ] Test: `test_debug_logs_queue_flush()` - verify queue flush events logged
- [ ] Implement: Log queue flush with message count in debug mode
- [ ] Run: `uv run pytest tests/webui/test_frontend_logging.py -v -k "queue_flush"`

---

## Phase 4: Log Policy Enforcement

### Normal Mode Quiet

- [ ] Test: `test_normal_mode_no_connection_logs()` - verify connection logs suppressed when debug=false
- [ ] Implement: Wrap lifecycle logs behind `this.debugEnabled` check
- [ ] Run: `uv run pytest tests/webui/test_frontend_logging.py -v -k "normal_mode"`

- [ ] Test: `test_normal_mode_no_message_payload_logs()` - verify message payloads not logged in normal mode
- [ ] Verify: Current implementation already guards debugStats behind debugEnabled
- [ ] Run: `uv run pytest tests/webui/test_frontend_logging.py -v -k "no_payload"`

### Error Logs Always Visible

- [ ] Test: `test_errors_always_logged()` - verify WebSocket errors logged even in normal mode
- [ ] Verify: Error logging should not be gated by debug flag
- [ ] Run: `uv run pytest tests/webui/test_frontend_logging.py -v -k "errors"`

---

## Phase 5: Integration Verification

### End-to-End Debug Flow

- [ ] Test: `test_e2e_debug_flag_flow()` - verify full chain: CLI → server → browser → console
- [ ] Manual: Run `alfred --log debug webui --log debug` and verify browser console shows prefixed logs
- [ ] Run: `uv run pytest tests/webui/test_e2e.py -v -k "debug_flow"`

### Log Prefix Consistency

- [ ] Test: `test_all_debug_logs_have_prefix()` - verify all debug logs use `[websocket]` prefix
- [ ] Verify: Check console method overrides apply prefix consistently
- [ ] Run: `uv run pytest tests/webui/test_frontend_logging.py -v -k "prefix"`

---

## Files to Modify

1. `src/alfred/cli/main.py`
   - Add `--log` option to `webui_app` callback
   - Store `_webui_log_level` for webui-specific logging

2. `src/alfred/cli/webui_hotswap.py`
   - Update `_build_server_controller` to accept and pass `debug` parameter
   - Update `run_webui_server` and `run_webui_hotswap` to accept debug flag

3. `src/alfred/interfaces/webui/static/js/websocket-client.js`
   - Add `[websocket]` prefix to lifecycle logs when debug enabled
   - Ensure all debug logs use consistent prefix
   - Keep error logs always visible

4. `tests/webui/test_webui_cli.py` (new or existing)
   - Add tests for `--log debug` flag on webui command
   - Add tests for debug flag propagation to server

5. `tests/webui/test_frontend_logging.py` (existing)
   - Add tests for debug lifecycle logging
   - Add tests for normal mode quiet behavior
   - Add tests for prefix consistency

## Commit Strategy

Each checkbox = one atomic commit:
- `test(webui-cli): verify webui --log debug flag accepted`
- `feat(webui-cli): add --log option to webui subcommand`
- `test(websocket): verify connection logs have prefix in debug mode`
- `feat(websocket): add [websocket] prefix to lifecycle logs`
- etc.

## Verification Commands

```bash
# Run CLI tests
uv run pytest tests/webui/test_webui_cli.py -v

# Run frontend logging tests
uv run pytest tests/webui/test_frontend_logging.py -v

# Run full Web UI test suite
uv run pytest tests/webui/ -v --timeout=60

# Manual verification
uv run alfred --log debug webui --log debug
# Open browser and check console for [websocket] prefixed logs
```

---

## Progress Tracking

**Started**: 2026-03-27

**Completed**:
- [x] Phase 1: CLI Flag Plumbing ✅
- [x] Phase 2: Browser Config Verification ✅
- [ ] Phase 3: Structured Lifecycle Logging
- [ ] Phase 4: Log Policy Enforcement
- [ ] Phase 5: Integration Verification

**Current Task**: Phase 3 - Structured Lifecycle Logging
