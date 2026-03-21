# Execution Plan: PRD #139 - Web UI Test Fixture Realism

## Overview

Implement PRD #139 by codifying the modern Web UI contract, replacing unrealistic Web UI fixtures with shared Protocol-backed fakes that use real production data models, migrating behavior tests onto that harness, and removing all test-only / legacy compatibility branches from `src/alfred/interfaces/webui/server.py`.

This plan is intentionally granular. Each test/implement/run triplet should be completed in order and committed atomically once green.

>Status: completed. The checklist below is retained as a historical record of the implementation work.

---

## Phase 1: Contract Surface and Shared Fake Harness

### 1.1 Add runtime-checkable Web UI Protocols

- [ ] **Test**: Create `tests/webui/test_contracts.py::test_webui_contracts_export_runtime_checkable_protocols`
  - Verify `WebUISessionManager`, `WebUICore`, and `WebUIAlfred` are importable and marked `@runtime_checkable`
- [ ] **Implement**: Create `src/alfred/interfaces/webui/contracts.py`
  - Add Protocols: `WebUISessionManager`, `WebUICore`, `WebUIAlfred`
  - Keep the surface limited to what `server.py` actually uses
- [ ] **Run**: `uv run pytest tests/webui/test_contracts.py::test_webui_contracts_export_runtime_checkable_protocols -v`

### 1.2 Create shared Web UI fakes built from real production models

- [ ] **Test**: Create `tests/webui/test_contracts.py::test_fake_alfred_builds_real_session_message_tool_call_and_token_objects`
  - Verify helpers return real `Session`, `SessionMeta`, `Message`, `ToolCallRecord`, and `TokenTracker` instances
- [ ] **Implement**: Create `tests/webui/fakes.py`
  - Add `make_session_meta()`
  - Add `make_message()`
  - Add `make_tool_call()`
  - Add `make_session()`
  - Add `FakeSessionManager`, `FakeCore`, and `FakeAlfred`
- [ ] **Run**: `uv run pytest tests/webui/test_contracts.py::test_fake_alfred_builds_real_session_message_tool_call_and_token_objects -v`

### 1.3 Prove the shared fakes satisfy the Protocols

- [ ] **Test**: Create `tests/webui/test_contracts.py::test_fake_alfred_and_fake_session_manager_satisfy_webui_protocols`
  - Use `isinstance(..., ProtocolType)` checks against the runtime-checkable Protocols
- [ ] **Implement**: Fill in any missing methods/attributes on `FakeSessionManager`, `FakeCore`, or `FakeAlfred`
  - `new_session_async()`
  - `resume_session_async()`
  - `list_sessions_async()`
  - `get_current_cli_session()`
  - `start_session()`
  - `chat_stream()`
  - `sync_token_tracker_from_session()`
- [ ] **Run**: `uv run pytest tests/webui/test_contracts.py::test_fake_alfred_and_fake_session_manager_satisfy_webui_protocols -v`

---

## Phase 2: Startup Contract and Status Parity

### 2.1 Remove fixture-only startup gating on dict-shaped config

- [ ] **Test**: Add `tests/webui/test_server_parity.py::test_websocket_connect_ignores_dict_config_when_contract_is_valid`
  - Build a contract-valid `FakeAlfred` that still exposes a dict-shaped `config`
  - Expect startup to send `connected`, `session.loaded`, and `status.update`
- [ ] **Implement**: Update `src/alfred/interfaces/webui/server.py`
  - Remove the startup gate that skips `_load_current_session()` / `_send_status_update()` when `config` is a dict
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_websocket_connect_ignores_dict_config_when_contract_is_valid -v`

### 2.2 Migrate startup parity coverage to shared fakes

- [ ] **Test**: Refactor `tests/webui/test_server_parity.py::test_websocket_connect_syncs_token_tracker_and_sends_status_update`
  - Replace bespoke local mock classes with imports from `tests/webui/fakes.py`
  - Preserve the existing assertions for restored token totals
- [ ] **Implement**: Update `tests/webui/test_server_parity.py`
  - Remove local `MockSession`, `MockSessionManager`, `MockCore`, and `MockAlfred` duplicates now covered by the shared harness
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_websocket_connect_syncs_token_tracker_and_sends_status_update -v`

---

## Phase 3: Session Command Contract Enforcement

### 3.1 Keep `/new` working through `core.session_manager.new_session_async()`

- [ ] **Test**: Refactor `tests/webui/test_server_parity.py::test_new_command_resets_status_totals_for_fresh_session`
  - Use `FakeAlfred` + `FakeSessionManager` from `tests/webui/fakes.py`
  - Assert `/new` still resets token totals to zero
- [ ] **Implement**: Update parity fixtures and any server type hints needed for the modern path only
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_new_command_resets_status_totals_for_fresh_session -v`

### 3.2 Reject legacy root-level `new_session` fallback

- [ ] **Test**: Add `tests/webui/test_server_parity.py::test_new_command_rejects_legacy_root_level_new_session_shape`
  - Provide an Alfred-like object with root-level `new_session()` but no `core.session_manager.new_session_async()`
  - Expect `chat.error` instead of `session.new`
- [ ] **Implement**: Update `_create_session()` in `src/alfred/interfaces/webui/server.py`
  - Remove fallback to root-level `new_session`
  - Fail clearly when the modern contract is missing
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_new_command_rejects_legacy_root_level_new_session_shape -v`

### 3.3 Keep `/resume` working through `core.session_manager.resume_session_async()`

- [ ] **Test**: Refactor `tests/webui/test_server_parity.py::test_resume_command_syncs_historical_tokens_for_resumed_session`
  - Use shared fakes and real session/message dataclasses
  - Preserve assertions for historical input/output/cache/reasoning totals
- [ ] **Implement**: Update parity fixtures and any helper signatures needed for the modern path only
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_resume_command_syncs_historical_tokens_for_resumed_session -v`

### 3.4 Reject legacy root-level `resume_session` fallback

- [ ] **Test**: Add `tests/webui/test_server_parity.py::test_resume_command_rejects_legacy_root_level_resume_session_shape`
  - Provide an Alfred-like object with root-level `resume_session()` but no `core.session_manager.resume_session_async()`
  - Expect `chat.error` instead of `session.loaded`
- [ ] **Implement**: Update `_resume_session()` in `src/alfred/interfaces/webui/server.py`
  - Remove fallback to root-level `resume_session`
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_resume_command_rejects_legacy_root_level_resume_session_shape -v`

### 3.5 Keep `/sessions` working through `core.session_manager.list_sessions_async()`

- [ ] **Test**: Refactor `tests/webui/test_server_parity.py::test_sessions_command_marks_current_session_and_uses_live_message_count`
  - Use shared fakes and real `SessionMeta` / `Session`
  - Preserve the live current-session message count assertion
- [ ] **Implement**: Update parity fixtures to source session metadata from `tests/webui/fakes.py`
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_sessions_command_marks_current_session_and_uses_live_message_count -v`

### 3.6 Reject legacy root-level `list_sessions` fallback

- [ ] **Test**: Add `tests/webui/test_server_parity.py::test_sessions_command_rejects_legacy_root_level_list_sessions_shape`
  - Provide an Alfred-like object with root-level `list_sessions()` but no `core.session_manager.list_sessions_async()`
  - Expect `chat.error` instead of `session.list`
- [ ] **Implement**: Update `_list_sessions()` in `src/alfred/interfaces/webui/server.py`
  - Remove fallback to root-level `list_sessions`
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_sessions_command_rejects_legacy_root_level_list_sessions_shape -v`

### 3.7 Reject legacy root-level `current_session` fallback

- [ ] **Test**: Add `tests/webui/test_server_parity.py::test_session_command_rejects_legacy_root_level_current_session_shape`
  - Provide an Alfred-like object with root-level `current_session` but no `core.session_manager.get_current_cli_session()`
  - Expect `chat.error` instead of `session.info`
- [ ] **Implement**: Update `_get_current_session()` in `src/alfred/interfaces/webui/server.py`
  - Remove fallback to root-level `current_session`
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_session_command_rejects_legacy_root_level_current_session_shape -v`

---

## Phase 4: `/context` Contract Enforcement

### 4.1 Keep `/context` on the shared `get_context_display()` path

- [ ] **Test**: Refactor `tests/webui/test_server_parity.py::test_context_command_uses_shared_context_display`
  - Use `FakeAlfred` from `tests/webui/fakes.py`
  - Keep the boundary patch on `alfred.context_display.get_context_display`
- [ ] **Implement**: Update parity fixtures to remove any remaining legacy context scaffolding
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_context_command_uses_shared_context_display -v`

### 4.2 Reject legacy `alfred.get_context()` fallback

- [ ] **Test**: Add `tests/webui/test_server_parity.py::test_context_command_rejects_legacy_get_context_shape`
  - Provide an Alfred-like object with `get_context()` but no valid `get_context_display()` path
  - Expect `chat.error` instead of `context.info`
- [ ] **Implement**: Update `_handle_context_command()` in `src/alfred/interfaces/webui/server.py`
  - Remove fallback to `alfred.get_context()`
- [ ] **Run**: `uv run pytest tests/webui/test_server_parity.py::test_context_command_rejects_legacy_get_context_shape -v`

---

## Phase 5: `tests/webui/test_chat.py` Migration

### 5.1 Replace the root-level `MagicMock` chat fixture

- [ ] **Test**: Refactor `tests/webui/test_chat.py::test_websocket_streams_chat_chunks`
  - Use `FakeAlfred` from `tests/webui/fakes.py`
  - Preserve the assembled content assertion
- [ ] **Implement**: Update `tests/webui/test_chat.py`
  - Remove `MagicMock`-based `mock_alfred` fixture
  - Replace it with a shared fake fixture built from `FakeAlfred`
- [ ] **Run**: `uv run pytest tests/webui/test_chat.py::test_websocket_streams_chat_chunks -v`

### 5.2 Migrate the `/new` command test off root-level `new_session`

- [ ] **Test**: Refactor `tests/webui/test_chat.py::test_websocket_handles_command_execute`
  - Assert `/new` works through `core.session_manager.new_session_async()`
  - Remove test setup that mutates `client_with_alfred.app.state.alfred.new_session`
- [ ] **Implement**: Update the command test to use `FakeSessionManager` state instead of monkeying a root-level async method onto the Alfred fixture
- [ ] **Run**: `uv run pytest tests/webui/test_chat.py::test_websocket_handles_command_execute -v`

### 5.3 Replace direct-helper `MagicMock` roots with explicit fakes and edge spies

- [ ] **Test**: Refactor `tests/webui/test_chat.py::test_chat_stream_integration`
  - Keep the direct `_handle_chat_message()` coverage
  - Replace root-level `MagicMock` Alfred with `FakeAlfred`
  - Keep `AsyncMock` only for the websocket spy
- [ ] **Implement**: Update `test_chat_stream_integration` and `test_chat_stream_error_handling`
  - Use shared fakes for Alfred behavior
  - Keep mocks only at the websocket boundary
- [ ] **Run**: `uv run pytest tests/webui/test_chat.py::test_chat_stream_integration -v`

---

## Phase 6: `tests/webui/test_integration.py` Migration

### 6.1 Replace legacy integration fixtures with shared fakes

- [ ] **Test**: Refactor `tests/webui/test_integration.py::test_full_chat_flow_single_message`
  - Use `FakeAlfred` from `tests/webui/fakes.py`
  - Preserve chat chunk ordering and status assertions
- [ ] **Implement**: Replace local `MockSession` / `MockAlfred` in `tests/webui/test_integration.py`
  - Remove root-level `new_session`, `resume_session`, `list_sessions`, `current_session`, and `get_context` fixture methods
- [ ] **Run**: `uv run pytest tests/webui/test_integration.py::TestFullChatFlow::test_full_chat_flow_single_message -v`

### 6.2 Keep the session workflow on the modern contract only

- [ ] **Test**: Refactor `tests/webui/test_integration.py::test_session_full_workflow`
  - Assert `/new`, `/sessions`, and `/resume` operate through `core.session_manager`
  - Preserve the session-count and session-switch assertions
- [ ] **Implement**: Update the integration fixture wiring to source all session behavior from `FakeSessionManager`
- [ ] **Run**: `uv run pytest tests/webui/test_integration.py::TestSessionManagementFlow::test_session_full_workflow -v`

---

## Phase 7: `tests/webui/test_websocket.py` Migration

### 7.1 Replace duplicate local session/message doubles with real dataclass helpers

- [ ] **Test**: Refactor `tests/webui/test_websocket.py::test_session_loaded_includes_tool_calls`
  - Build the assistant message with real `Message` + `ToolCallRecord`
  - Build the session with `make_session()` from `tests/webui/fakes.py`
- [ ] **Implement**: Remove bespoke local message/session helper types that are now duplicated by the shared harness
- [ ] **Run**: `uv run pytest tests/webui/test_websocket.py::TestWebSocketSessionRestore::test_session_loaded_includes_tool_calls -v`

### 7.2 Replace duplicate local Alfred/session manager doubles with shared fakes

- [ ] **Test**: Refactor `tests/webui/test_websocket.py::test_command_new_session`
  - Use `FakeAlfred` + `FakeSessionManager`
  - Preserve existing `/new` assertions
- [ ] **Implement**: Update the command/status/debug fixtures in `tests/webui/test_websocket.py` to import from `tests/webui/fakes.py`
- [ ] **Run**: `uv run pytest tests/webui/test_websocket.py::TestWebSocketCommandsWithMockedAlfred::test_command_new_session -v`

### 7.3 Keep websocket startup/status tests green on the shared harness

- [ ] **Test**: Refactor `tests/webui/test_websocket.py::TestWebSocketStatusUpdates::test_status_update_token_counts`
  - Use shared fakes and real `TokenTracker`
  - Preserve assertions for `contextTokens`, `inputTokens`, and `outputTokens`
- [ ] **Implement**: Remove any remaining duplicated token/session scaffolding in `tests/webui/test_websocket.py`
- [ ] **Run**: `uv run pytest tests/webui/test_websocket.py::TestWebSocketStatusUpdates::test_status_update_token_counts -v`

---

## Phase 8: Tool-Call Behavior Realism

### 8.1 Add a websocket-level tool-call behavior test

- [ ] **Test**: Add `tests/webui/test_tool_calls.py::test_tool_call_websocket_flow_emits_start_output_and_end`
  - Drive the flow through `/ws`
  - Use `FakeAlfred.chat_stream(..., tool_callback=...)` to emit `ToolStart`, `ToolOutput`, and `ToolEnd`
  - Assert the browser-facing websocket protocol emits `tool.start`, `tool.output`, and `tool.end`
- [ ] **Implement**: Update `tests/webui/test_tool_calls.py`
  - Add a websocket-driven behavior test using `FakeAlfred`
  - Keep the existing direct `_handle_chat_message()` helper test only if it still covers a narrow internal detail not already covered by websocket behavior
- [ ] **Run**: `uv run pytest tests/webui/test_tool_calls.py::test_tool_call_websocket_flow_emits_start_output_and_end -v`

### 8.2 Narrow any remaining direct helper tests to internal concerns only

- [ ] **Test**: Refactor the direct helper coverage in `tests/webui/test_tool_calls.py`
  - Make the remaining helper test assert only batching or event-order details that are awkward to express through the websocket boundary
- [ ] **Implement**: Remove any helper test assertions that duplicate websocket behavior coverage
- [ ] **Run**: `uv run pytest tests/webui/test_tool_calls.py -q --timeout=30`

---

## Phase 9: Production Cleanup and Guardrails

### 9.1 Delete `MagicMock` branches from `server.py`

- [ ] **Refactor**: Remove `from unittest.mock import MagicMock` from `src/alfred/interfaces/webui/server.py`
  - Delete all `isinstance(..., MagicMock)` checks now covered by the parity and migration tests above
- [ ] **Run**: `rg -n "MagicMock" src/alfred/interfaces/webui/server.py`

### 9.2 Narrow server type hints to the new Protocols

- [ ] **Refactor**: Update `src/alfred/interfaces/webui/server.py`
  - Type `create_app()` as accepting `WebUIAlfred | None`
  - Type helper functions around `WebUIAlfred` / `WebUISessionManager` where practical
- [ ] **Run**: `uv run mypy --strict src/alfred/interfaces/webui src/alfred/interfaces/webui/contracts.py`

### 9.3 Document the fake-harness guardrails where contributors will see them

- [ ] **Refactor**: Add a short module docstring / comment block in `tests/webui/fakes.py`
  - Explain that Web UI tests use Protocol-backed fakes
  - Explain that session/message/tool/token state uses real production classes
  - Explain that root-level bare `MagicMock` Alfred fixtures are forbidden here
- [ ] **Run**: `uv run pytest tests/webui/test_contracts.py -q --timeout=30`

---

## Phase 10: Browser Smoke and Final Verification

### 10.1 Browser smoke already exists in the repo

- [x] Existing browser smoke coverage in `tests/webui/test_kidcore_browser.py` already verifies Web UI startup and connection behavior; no new `tests/webui/test_browser_smoke.py` file was needed.

### 10.2 Run the full verification sweep

- [x] `uv run pytest tests/webui/test_contracts.py -q --timeout=30`
- [x] `uv run pytest tests/webui/test_server_parity.py -q --timeout=30`
- [x] `uv run pytest tests/webui/test_chat.py -q --timeout=30`
- [x] `uv run pytest tests/webui/test_integration.py -q --timeout=30`
- [x] `uv run pytest tests/webui/test_websocket.py -q --timeout=30`
- [x] `uv run pytest tests/webui/test_tool_calls.py -q --timeout=30`
- [x] `uv run pytest tests/webui -q --timeout=30`
- [x] `uv run ruff check src/ tests/webui/`
- [x] `uv run mypy --strict src/`
- [x] `uv run alfred webui --port 8080`

---

## Files to Modify

1. `src/alfred/interfaces/webui/contracts.py` - new Protocol definitions for the Web UI contract
2. `src/alfred/interfaces/webui/server.py` - remove test-only and legacy fallback branches; tighten types
3. `tests/webui/fakes.py` - shared Web UI fake harness built from real production models
4. `tests/webui/test_contracts.py` - new runtime Protocol and fake-harness tests
5. `tests/webui/test_server_parity.py` - parity tests for startup, session commands, status sync, and `/context`
6. `tests/webui/test_chat.py` - remove root-level `MagicMock` Alfred fixture and migrate helper tests
7. `tests/webui/test_integration.py` - replace legacy root-level Alfred fixture shape with shared fakes
8. `tests/webui/test_websocket.py` - replace duplicate local doubles with the shared harness
9. `tests/webui/test_tool_calls.py` - add websocket-level tool-call behavior coverage; keep helper tests narrow
10. `tests/webui/test_browser_smoke.py` - add browser startup smoke if no generic smoke exists already

---

## Commit Strategy

Each green test/implement/run triplet should become one atomic conventional commit.

Suggested commit sequence:
- `test(webui): add runtime protocol contract checks`
- `test(webui): add shared fake harness with real session models`
- `fix(webui): remove dict-config startup gate`
- `fix(webui): require session manager for new command`
- `fix(webui): require session manager for resume command`
- `fix(webui): require session manager for sessions command`
- `fix(webui): require session manager for current session lookup`
- `fix(webui): remove legacy get_context fallback`
- `test(webui): migrate chat tests to shared fake harness`
- `test(webui): migrate integration tests to shared fake harness`
- `test(webui): migrate websocket tests to shared fake harness`
- `test(webui): add websocket tool-call behavior coverage`
- `refactor(webui): remove magicmock branches from server`
- `test(webui): add browser startup smoke coverage`

---

## Next Recommended Task

None. PRD #139 implementation and Web UI verification are complete.

Use the PRD close workflow if this issue should be closed.
