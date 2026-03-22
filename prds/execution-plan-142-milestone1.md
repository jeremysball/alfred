# Execution Plan: PRD #142 - Milestone 1

## Overview

Define the daemon status contract that will eventually power the Web UI popover, while keeping daemon health separate from the token/status stream.

This milestone is intentionally limited to the contract and backend snapshot plumbing. The current Web UI can keep using the legacy `/health` fields for compatibility; later milestones will switch the frontend over to `daemon.status`, autostart the daemon, and add richer live telemetry.

---

## Milestone 1: Daemon contract is explicit and separate from `status.update`

### Component: Protocol surface

- [x] **Test**: `test_daemon_status_message_structure()` — `daemon.status` validates a nested `daemon` object with `state`, `pid`, `socketPath`, `socketHealthy`, `startedAt`, `uptimeSeconds`, `lastHeartbeatAt`, `lastReloadAt`, and `lastError`
- [x] **Test**: `test_status_update_message_has_no_daemon_fields()` — `status.update` stays focused on model/token/queue state only
- [x] **Implement**: update `src/alfred/interfaces/webui/protocol.py` and `src/alfred/interfaces/webui/validation.py`
  - add `DaemonStatusInfo`
  - add `DaemonStatusPayload`
  - add `DaemonStatusMessage`
  - remove daemon fields from `StatusUpdatePayload`
- [x] **Run**: `uv run pytest tests/webui/test_protocol.py::test_daemon_status_message_structure tests/webui/test_protocol.py::test_status_update_message_has_no_daemon_fields tests/webui/test_validation.py -v`

### Component: Shared daemon snapshot helper

- [x] **Test**: `test_build_daemon_status_reports_running_daemon_and_socket_health()` — a running daemon with a connected socket client produces a `running` snapshot with PID and socket path
- [x] **Test**: `test_build_daemon_status_handles_stopped_or_failed_daemon()` — a missing PID or startup error produces the expected degraded snapshot fields
- [x] **Implement**: add `src/alfred/interfaces/webui/daemon_status.py`
  - centralize daemon snapshot assembly in one helper
  - derive state/PID from `DaemonManager`
  - derive socket health/path from the Web UI Alfred socket client when available
  - allow null/default values for fields not yet populated by later milestones
- [x] **Implement**: extend `tests/webui/fakes.py`
  - add a small `FakeSocketClient`
  - attach it to `FakeAlfred` so daemon snapshot tests stay explicit and contract-shaped
- [x] **Run**: `uv run pytest tests/webui/test_daemon_status.py -v`

### Component: WebSocket startup and health payloads

- [x] **Test**: `test_websocket_connect_emits_daemon_status_and_status_update_separately()` — websocket startup emits `session.loaded`, then `daemon.status`, then `status.update`, with daemon data living only in `daemon.status`
- [x] **Test**: `test_health_endpoint_includes_daemon_snapshot()` — `/health` reuses the same daemon snapshot helper while keeping the current legacy daemon fields for compatibility
- [x] **Implement**: update `src/alfred/interfaces/webui/server.py`
  - send `daemon.status` during websocket startup
  - stop injecting daemon fields into `status.update`
  - reuse the shared daemon helper in `/health`
  - keep the legacy top-level `/health` daemon fields until later frontend work consumes the nested daemon payload
- [x] **Implement**: update the Web UI test startup helpers that currently assume `connected -> session.loaded -> status.update`
  - `tests/webui/test_chat.py`
  - `tests/webui/test_keepalive.py`
  - `tests/webui/test_websocket.py`
  - `tests/webui/test_integration.py`
  - `tests/webui/test_reconnect.py`
  - `tests/webui/test_tool_calls.py`
  - `tests/webui/test_keepalive_browser.py`
  - `tests/webui/test_server_parity.py`
- [x] **Run**: `uv run pytest tests/webui/test_server_parity.py tests/webui/test_server.py tests/webui/test_chat.py tests/webui/test_keepalive.py tests/webui/test_websocket.py tests/webui/test_integration.py tests/webui/test_reconnect.py tests/webui/test_tool_calls.py tests/webui/test_keepalive_browser.py -q --timeout=30`

---

## Files to Modify

1. `src/alfred/interfaces/webui/protocol.py` — add daemon message types, remove daemon fields from token status
2. `src/alfred/interfaces/webui/validation.py` — add daemon validation models, keep `status.update` narrow
3. `src/alfred/interfaces/webui/daemon_status.py` — new shared daemon snapshot helper
4. `src/alfred/interfaces/webui/server.py` — emit `daemon.status` and reuse the helper in `/health`
5. `tests/webui/test_protocol.py` — daemon contract coverage
6. `tests/webui/test_validation.py` — daemon validation coverage
7. `tests/webui/test_daemon_status.py` — new helper tests
8. `tests/webui/test_server.py` — `/health` snapshot coverage
9. `tests/webui/test_server_parity.py` — websocket startup contract coverage
10. `tests/webui/test_chat.py` — startup helper needs to consume `daemon.status`
11. `tests/webui/test_keepalive.py` — startup helper needs to consume `daemon.status`
12. `tests/webui/test_websocket.py` — startup helper needs to consume `daemon.status`
13. `tests/webui/test_integration.py` — startup helper needs to consume `daemon.status`
14. `tests/webui/test_reconnect.py` — startup helper needs to consume `daemon.status`
15. `tests/webui/test_tool_calls.py` — startup helper needs to consume `daemon.status`
16. `tests/webui/test_keepalive_browser.py` — browser websocket startup sequence needs to consume `daemon.status`
17. `tests/webui/fakes.py` — explicit fake socket client for daemon snapshot tests

---

## Commit Strategy

Each completed checkbox should be one atomic change:
- `test(webui): add daemon.status contract coverage`
- `feat(webui): add shared daemon snapshot helper`
- `feat(webui): emit daemon status separately from token status`

Do not batch schema changes, snapshot assembly, and server wiring into one commit.

---

## Exit Criteria for Milestone 1

- `daemon.status` exists as a first-class Web UI contract
- daemon/runtime data is no longer mixed into `status.update`
- the backend has one shared helper for building daemon snapshots
- websocket startup and `/health` consume the same daemon view
- later milestones can add autostart and live UI refinements without changing the schema
