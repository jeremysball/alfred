# PRD: Web UI Daemon Autostart and Runtime Status Popover

**GitHub Issue**: [#142](https://github.com/jeremysball/alfred/issues/142)  
**Status**: Draft  
**Priority**: High  
**Created**: 2026-03-21

---

## 1. Problem Statement

The Web UI currently assumes the daemon is managed separately, but that separation is not obvious to users.

When someone opens the Web UI today:
- the browser can connect to the WebSocket server even when the daemon is not running or not healthy
- the daemon is not started automatically from the Web UI launch path
- the connection indicator in the header is only a tiny dot, so it does not communicate whether the app is connected, reconnecting, or degraded
- there is no place in the Web UI to inspect daemon PID, uptime, socket health, heartbeat age, or the last error/reload state

That creates two user problems:
1. **Operational friction** — users have to remember a separate daemon lifecycle.
2. **Debugging friction** — when something is wrong, the UI does not show enough context to tell whether the issue is the browser connection, the WebSocket server, or the daemon.

This PRD fixes the immediate user experience and keeps the architecture pointed toward a future unified runtime where frontends talk over WebSocket and background work is owned by one server host.

---

## 2. Goals & Success Criteria

### Goals
1. Start the daemon automatically when the Web UI launches, if it is not already running.
2. Replace the tiny connection dot with a live hover/focus popover.
3. Show detailed websocket connection state and daemon runtime status in one place.
4. Keep the popover live-updating so it feels snappy and current.
5. Preserve a clean migration path toward a unified server/runtime architecture.

### Success Criteria
- Launching `uv run alfred webui` from a stopped state starts the daemon without manual intervention.
- If the daemon cannot start, the Web UI still loads and clearly shows a degraded/error state instead of failing silently.
- Hovering or focusing the connection indicator shows:
  - **WebSocket**: endpoint URL, state, connected/reconnecting/disconnected status, reconnect attempts, last pong age or latency, queued outbound messages, last inbound/outbound message type
  - **Daemon**: running/stopped/starting/failed state, PID, uptime, socket health, last heartbeat age, last reload time, last error
- The popover updates live while visible, without requiring a page refresh.
- The Web UI still launches successfully and passes browser-level smoke checks.
- The implementation adds test coverage for startup behavior, status rendering, and failure/reconnect states.

---

## 3. Proposed Solution

### 3.1 Web UI bootstraps the daemon

The Web UI launch path should check daemon health during startup and start the daemon if needed.

Key behaviors:
- the bootstrap step must be idempotent
- if the daemon is already running, the Web UI should continue normally
- if the daemon start fails, the Web UI should remain usable and expose the failure clearly in the runtime status UI
- the bootstrap logic should live in a shared helper so the future unified server can reuse it

### 3.2 Add a runtime status surface separate from LLM token status

`status.update` already means LLM/token progress, so it should stay focused on that.

Introduce a separate runtime status surface for daemon and startup health. The frontend should compose:
- **client-side websocket state** from the browser WebSocket client
- **server-side runtime state** from the backend status snapshot

A good first-pass payload shape is something like:

```json
{
  "type": "runtime.status",
  "payload": {
    "daemon": {
      "state": "running",
      "pid": 12345,
      "startedAt": "2026-03-21T12:00:00Z",
      "uptimeSeconds": 183,
      "socketPath": "/home/node/.cache/alfred/daemon.sock",
      "lastHeartbeatAt": "2026-03-21T12:03:00Z",
      "lastReloadAt": "2026-03-21T12:02:41Z",
      "lastError": null
    }
  }
}
```

The backend can refresh this snapshot on startup, on reconnect, and on a short interval while clients are connected.

### 3.3 Replace the connection dot with a live popover

The connection indicator should become an interactive status surface instead of a decorative dot.

Desired UX:
- desktop: hover and keyboard focus open the popover
- touch/mobile: tap toggles the popover
- the popover shows a compact summary at the top and detailed stats below
- the design should keep working across themes

The popover should clearly separate:
- websocket connectivity details
- daemon runtime details

### 3.4 Shape the work for the future unified server

This PRD is not the full unification effort yet.

Instead, it should establish a shared runtime contract that can later be reused when the cron daemon and WebSocket server collapse into one host. The important architectural rule is: **the frontend should not care whether the daemon is a separate process today or a subsystem of a unified server tomorrow**.

That means:
- keep daemon bootstrap behind a shared runtime helper
- keep runtime status behind a single backend snapshot/message contract
- keep the frontend consuming a stable runtime model rather than process-specific hacks

---

## 4. Technical Implementation

### Likely file changes

```text
src/alfred/cli/webui_hotswap.py              # or shared startup helper for daemon bootstrap
src/alfred/cli/main.py                       # webui entrypoint wiring, if needed
src/alfred/interfaces/webui/server.py       # runtime status broadcast / startup hooks
src/alfred/interfaces/webui/protocol.py      # runtime.status message types
src/alfred/interfaces/webui/static/js/websocket-client.js
src/alfred/interfaces/webui/static/js/main.js
src/alfred/interfaces/webui/static/js/components/...   # popover component, if extracted
src/alfred/interfaces/webui/static/css/base.css
src/alfred/interfaces/webui/static/css/themes/*.css
src/alfred/cron/daemon.py                    # daemon state helpers, if needed
src/alfred/cron/daemon_cli.py                # optional shared startup/status helper extraction

tests/webui/test_*.py                        # startup, runtime status, and popover behavior tests
```

### Implementation notes

- The Web UI should own daemon bootstrap at launch time, not lazily only after the first user interaction.
- The browser WebSocket client should continue to own its own connection state; it can expose that state to the popover without waiting for a backend round trip.
- The backend should publish daemon/runtime state in a way that is cheap to refresh and easy to reuse later.
- Live updates should feel immediate, but the implementation should avoid noisy polling when the popover is closed.
- If the daemon is unavailable or fails during startup, the UI should show a degraded state with enough detail to diagnose the failure.

---

## 5. Milestones

### Milestone 1: Define the runtime contract

Lock down the runtime data model that will feed the popover and startup state.

Validation: the new runtime status payload is explicit, stable, and separate from `status.update`.

### Milestone 2: Autostart the daemon from the Web UI launch path

Make `uv run alfred webui` bring up the daemon when needed and continue cleanly when it is already running.

Validation: the Web UI starts from a cold state without manual daemon commands.

### Milestone 3: Expose daemon runtime health to the Web UI

Publish a live backend snapshot that includes daemon state, PID, uptime, socket health, heartbeat age, reload time, and last error.

Validation: runtime status changes show up in the UI when the daemon starts, stops, reloads, or fails.

### Milestone 4: Turn the connection dot into a popover

Replace the header dot with a focusable, hoverable, touch-friendly status popover.

Validation: the UI shows websocket and daemon details in a readable, accessible layout.

### Milestone 5: Make the popover live-updating

Keep the popover in sync with the latest websocket and daemon status while it is visible.

Validation: state changes are reflected quickly enough to feel live.

### Milestone 6: Add behavioral and browser-level tests

Cover startup, live status updates, reconnect states, and degraded/error behavior with realistic Web UI tests.

Validation: the Web UI test suite proves the popover and startup flow work through the real interface.

### Milestone 7: Update docs and record the unified-server follow-up direction

Document the new runtime status behavior and capture the architectural boundary for the future unified server plan.

Validation: the docs explain the new status surface and the follow-up direction is clear.

---

## 6. Validation Strategy

### Required checks
- `uv run pytest tests/webui/test_server_parity.py -q --timeout=30`
- `uv run pytest tests/webui/test_websocket.py -q --timeout=30`
- `uv run pytest tests/webui/test_integration.py -q --timeout=30`
- `uv run pytest tests/webui -q --timeout=30`
- `uv run ruff check src/ tests/webui/`
- `uv run mypy --strict src/`
- `uv run alfred webui --port 8080`
- Run a browser-level smoke check that verifies the connection indicator opens the status popover and shows fresh data

### What success looks like
- The Web UI starts the daemon automatically when needed.
- The header indicator makes connection health obvious at a glance.
- Hover/focus reveals the right amount of detail for troubleshooting.
- Status updates feel live, not stale.
- The app still launches reliably in the real browser path.

---

## 7. Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Autostart creates startup coupling between Web UI and daemon | Medium | Medium | Make startup idempotent and fail-soft; keep bootstrap in a shared helper |
| Live status polling becomes noisy or expensive | Medium | Medium | Update only when needed and keep the refresh cadence lightweight |
| The popover becomes a second status bar and gets cluttered | Medium | Low | Keep the summary compact and move details into grouped sections |
| The new runtime contract drifts into a second compatibility layer | High | Low | Keep the contract narrow and centered on the real runtime data the UI needs |
| The future unified-server plan expands this PRD beyond its scope | Medium | Medium | Treat unification as follow-up architecture work, not a required deliverable here |

---

## 8. Non-Goals

- Full unification of the cron daemon and WebSocket server in this PRD
- A complete visual redesign of the entire Web UI
- New authentication or multi-user support
- Changes to the chat streaming protocol or `status.update` semantics
- Replacing existing CLI daemon commands immediately
- A large general-purpose admin console in the header popover

---

## 9. Future Direction

The runtime bootstrap and status contract defined here should be reusable in a later plan that merges the daemon and WebSocket server into one unified runtime.

That follow-up plan should:
- keep frontends talking over WebSocket
- move cron/background work under the same runtime host
- preserve the same status surface so the frontend does not need to change again
- remove process-boundary assumptions from the backend over time

This PRD should shape the work so that future unification is straightforward, but it should not try to complete that merge now.

---

## 10. Resolved Design Decisions

1. **Web UI should start the daemon automatically** when the app launches.
2. **The connection indicator should be a custom popover**, not a native tooltip.
3. **The popover should live-update** while visible.
4. **Detailed stats should include** websocket URL/state/reconnect attempts/last pong plus daemon PID/uptime/socket/heartbeat/last error.
5. **Runtime status should be separate from `status.update`** so LLM status and daemon health stay decoupled.
6. **The unified-server effort is a follow-up direction**, not a required deliverable in this PRD.

---

## 11. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-21 | Auto-start the daemon from the Web UI launch path | Users should not have to manage a separate daemon step just to use the Web UI |
| 2026-03-21 | Use a custom hover/focus popover for the connection indicator | Native tooltips are too limited for the level of detail and live updates we want |
| 2026-03-21 | Keep websocket connection state client-side and daemon health server-side | This cleanly separates browser telemetry from backend runtime state |
| 2026-03-21 | Introduce a runtime status surface separate from `status.update` | LLM token/status updates and daemon runtime status are different concerns |
| 2026-03-21 | Treat cron/websocket unification as a follow-up architecture plan | The immediate UX fix should not be blocked by the full server merge |
