# Execution Plan: PRD #142 - Milestone 2

## Overview

Make `uv run alfred webui` bring up the daemon automatically when needed, keep the launch path idempotent, and preserve a degraded-but-usable UI when bootstrap fails.

This milestone builds on the `daemon.status` contract from Milestone 1 and threads daemon bootstrap state through the Web UI launch path so the status surface can report startup success or failure.

---

## Phase 2: Web UI launch path autostarts the daemon

### Component: Shared bootstrap helper contract

- [x] **Test**: `test_bootstrap_daemon_starts_when_daemon_is_missing()` — the helper asks the daemon to start and reports success when no PID is running
- [x] **Test**: `test_bootstrap_daemon_noops_when_daemon_is_already_running()` — the helper skips bootstrap work when the daemon is already healthy
- [x] **Test**: `test_bootstrap_daemon_reports_failure_when_startup_fails()` — the helper returns a failure result and startup error when the daemon cannot be started
- [x] **Implement**: add `src/alfred/interfaces/webui/daemon_bootstrap.py`
  - define a small bootstrap result object
  - reuse the existing daemon start logic instead of duplicating subprocess management
  - keep the helper side-effect free except for the daemon start attempt
- [x] **Run**: `uv run pytest tests/webui/test_daemon_bootstrap.py -v`

### Component: Web UI launch wiring

- [x] **Test**: `test_run_webui_server_bootstraps_daemon_before_starting_uvicorn()` — the server build path calls the bootstrap helper before the Uvicorn controller starts
- [x] **Test**: `test_run_webui_hotswap_uses_the_same_bootstrap_path()` — hotswap restarts reuse the same bootstrap helper on each launch cycle
- [x] **Implement**: update `src/alfred/cli/webui_hotswap.py`
  - call the shared bootstrap helper during server construction
  - stash the bootstrap result on app state for downstream health/status rendering
  - keep the already-running daemon path a no-op
- [x] **Run**: `uv run pytest tests/test_cli_webui_startup.py tests/webui/test_hotswap.py -v`

### Component: Bootstrap failure visibility

- [x] **Test**: `test_health_endpoint_includes_bootstrap_failure_when_app_state_sets_error()` — `/health` exposes a startup failure in the nested daemon snapshot and legacy top-level fields
- [x] **Test**: `test_websocket_connect_emits_failed_daemon_status_when_bootstrap_error_is_present()` — initial websocket startup status shows the failed daemon state when bootstrap error is present
- [x] **Implement**: update `src/alfred/interfaces/webui/server.py`
  - read bootstrap error from app state when building `/health` and initial `daemon.status`
  - continue serving the Web UI even when bootstrap fails
  - keep the success path unchanged when the daemon starts cleanly
- [x] **Run**: `uv run pytest tests/webui/test_server.py tests/webui/test_server_parity.py -v`

### Component: Launch acceptance coverage

- [x] **Test**: `test_webui_launch_path_starts_daemon_from_cold_state()` — launching `alfred webui` from a stopped state requests daemon autostart before the server becomes available
- [x] **Test**: `test_webui_launch_path_still_serves_health_after_bootstrap_failure()` — the process still responds to `/health` if daemon bootstrap fails
- [x] **Implement**: extend the launch smoke coverage in `tests/webui/test_components.py` and any CLI startup harness needed for the autostart check
- [x] **Run**: `uv run pytest tests/webui/test_components.py tests/test_cli_webui_startup.py -q --timeout=30`

---

## Files to Modify

1. `src/alfred/interfaces/webui/daemon_bootstrap.py` — new shared daemon autostart helper
2. `src/alfred/cli/webui_hotswap.py` — call the helper and stash bootstrap state
3. `src/alfred/interfaces/webui/server.py` — surface bootstrap failure in `/health` and initial `daemon.status`
4. `tests/webui/test_daemon_bootstrap.py` — helper contract coverage
5. `tests/test_cli_webui_startup.py` — launch wiring coverage
6. `tests/webui/test_server.py` — `/health` failure-path coverage
7. `tests/webui/test_server_parity.py` — websocket startup failure-path coverage
8. `tests/webui/test_hotswap.py` — confirm the hotswap path shares the same bootstrap helper
9. `tests/webui/test_components.py` — process-level smoke coverage

## Commit Strategy

Each completed checkbox should be one atomic change:
- `test(webui): cover daemon bootstrap helper`
- `feat(webui): autostart daemon during webui launch`
- `test(webui): cover webui launch bootstrap failure`

Do not batch helper creation, launch wiring, and smoke coverage into one commit.

---

## Exit Criteria for Milestone 2

- `uv run alfred webui` starts the daemon when needed
- launching the Web UI twice does not duplicate bootstrap work when the daemon is already running
- bootstrap failures do not block the UI from serving
- the Web UI status surface can report startup problems from app state
- later milestone work can build on a stable launch path
