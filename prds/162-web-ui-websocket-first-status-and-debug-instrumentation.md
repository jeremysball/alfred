# PRD: Web UI WebSocket-First Status and Debug Instrumentation

**GitHub Issue**: [#162](https://github.com/jeremysball/alfred/issues/162)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-03-27

---

## Problem

The Web UI currently splits live state across WebSocket events and HTTP health checks. That makes the connection pill, status popover, and message-sending flow harder to trust because the UI can look healthy even when the socket is reconnecting, stale, or unavailable.

Debugging is also too opaque. We need clear server logs, browser/client logs, and connection lifecycle instrumentation without reintroducing noisy per-message console spam.

---

## Solution

Make the Web UI WebSocket-first for all live runtime state:

- Use WebSocket messages and snapshots as the source of truth for connection status and message flow
- Keep `/health` as an ops/readiness endpoint only, not a live UI dependency
- Ensure message sending stays on the WebSocket path
- Add explicit debug instrumentation for both server and browser/client surfaces
- Support the operator workflow `alfred --log debug webui --log debug`, where the top-level flag controls Alfred/server logs and the Web UI flag enables browser/client instrumentation

---

## User Experience

### Open the Web UI

- The connection pill reflects the actual socket state immediately
- The popover shows live WebSocket status, reconnect state, ping/pong health, and daemon snapshot data
- The UI does not need to fetch `/health` to determine live connection state

### Send a message

- Messages are sent over WebSocket only
- If the socket reconnects, the UI makes that state visible instead of silently hiding it
- The user sees a stable retry/reconnect experience rather than a confusing mix of HTTP and socket behavior

### Debug a problem

- `alfred --log debug` emits server-side operational logs
- `alfred webui --log debug` enables browser/client instrumentation and structured connection logs
- Logs summarize connection lifecycle and transport health instead of dumping every message payload

---

## Technical Scope

### Live State Source of Truth

- Handle WebSocket startup and runtime messages directly in the browser client
- Consume `daemon.status` as the runtime daemon snapshot for the connection status popover
- Treat `status.update` as conversation/session telemetry only
- Ignore or explicitly no-op startup messages that are not meant to mutate UI state

### Health Endpoint Boundary

- Keep `/health` in the backend for readiness, ops checks, and external monitoring
- Remove `/health` from the Web UI runtime status path
- If the WebSocket startup or daemon snapshot fails, surface that through the live socket path rather than falling back to HTTP

### Debug and Logging

- Add browser/client debug wiring behind the Web UI debug flag
- Keep console output prefixed and stable for browser logs
- Log connection lifecycle events with useful summaries:
  - connect / disconnect / reconnect
  - close code and reason
  - ping / pong timing
  - queue flushes
  - startup or transport failures
- Avoid per-message payload dumps in normal operation

### Reconnect Reliability

- Make connection attempts idempotent
- Prevent duplicate lifecycle listeners and reconnect storms
- Surface reconnecting state explicitly in the UI
- Ensure send operations remain safe during transient disconnects

---

## Implementation Milestones

### Milestone 1: Define the WebSocket-first runtime contract
**Goal**: Establish a single source of truth for live Web UI state.

**Scope**:
- Document which messages mutate live UI state
- Treat `daemon.status` as the runtime daemon snapshot
- Keep `status.update` focused on conversation/session telemetry
- Ensure startup message handling does not create console noise

**Validation**:
- Browser startup shows the correct live state without relying on `/health`
- Startup protocol messages are consumed intentionally, not as unhandled noise

---

### Milestone 2: Drive the connection pill and popover from WebSocket state
**Goal**: Make the visible connection status accurate and responsive.

**Scope**:
- Update the connection pill for connected, disconnected, and reconnecting states
- Render the popover from the WebSocket snapshot and daemon snapshot data
- Remove runtime dependency on HTTP health hydration from the Web UI
- Keep `/health` available for ops/readiness use

**Validation**:
- The pill and popover match the actual socket state in desktop and mobile layouts
- The popover still shows daemon and keepalive details while the app remains WebSocket-first

---

### Milestone 3: Make message sending and reconnect behavior robust
**Goal**: Ensure messages continue to send correctly across disconnects and reconnects.

**Scope**:
- Make `connect()` idempotent across open/connecting/closing states
- Clean up reconnect and lifecycle listeners so repeated connects do not leak handlers
- Keep queue flushing and resend behavior predictable during transient disconnects
- Preserve the current WebSocket transport for send operations

**Validation**:
- A transient disconnect does not lose messages or wedge the composer
- Reconnect behavior remains stable across visibility changes, page restores, and pull-to-refresh

---

### Milestone 4: Add intentional debug instrumentation and log policy
**Goal**: Make failures diagnosable without flooding the console.

**Scope**:
- Wire the Web UI debug flag through CLI startup into browser/client config
- Distinguish global Alfred/server debug logs from Web UI/client debug logs
- Emit structured summaries for connection lifecycle, ping/pong, close reasons, and queue flushes
- Keep normal mode quiet and avoid raw per-message spam

**Validation**:
- `alfred --log debug` shows server logs useful for backend diagnosis
- `alfred webui --log debug` enables browser/client debug summaries and instrumentation
- Normal mode stays readable and does not dump every message payload

---

### Milestone 5: Add regression coverage for protocol, UI, and logging
**Goal**: Lock the behavior with browser and server tests.

**Scope**:
- Verify startup handling does not produce unhandled-message console noise
- Verify the connection popover reflects WebSocket state without HTTP hydration
- Verify reconnect and send behavior under transient disconnects
- Verify debug config wiring and log summaries in debug mode

**Validation**:
- Existing Web UI tests pass with the new contract
- Browser regression tests cover desktop and mobile connection states
- Debug-mode tests assert meaningful logs rather than raw payload spam

---

### Milestone 6: Update docs and rollout guidance
**Goal**: Make the new behavior discoverable and supportable.

**Scope**:
- Document the `alfred --log debug webui --log debug` workflow
- Clarify that `/health` is ops/readiness only
- Document how to interpret connection and debug logs when troubleshooting

**Validation**:
- CLI and Web UI logging guidance is easy to find
- The new behavior is understandable without reading source code

---

## Success Criteria

- [ ] The Web UI no longer depends on `/health` for live runtime status
- [ ] The connection pill and popover accurately reflect WebSocket state
- [ ] Message sending remains WebSocket-based and survives transient reconnects
- [ ] The browser console uses intentional, prefixed debug logging when enabled
- [ ] Global server logs and Web UI/client logs are independently useful
- [ ] No startup console noise from unhandled protocol messages
- [ ] `/health` continues to serve readiness and ops monitoring

---

## Risks

- **State drift between WebSocket and health payloads**: keep the UI on a single live source of truth and cover it with tests.
- **Reconnect storms on unstable networks**: make connect/reconnect idempotent and remove duplicate listeners.
- **Too much debug noise**: log summaries and structured state transitions instead of raw message payloads.
- **Startup failures hidden by the new UI path**: surface transport/bootstrap failures through the WebSocket startup sequence and tests.

---

## Dependencies

- Existing WebSocket startup sequence and protocol messages
- Browser/client config delivery via `/app-config.js`
- CLI flag plumbing for `webui --log debug`
- Existing Web UI browser test coverage
- Current `/health` readiness response shape

---

## Validation Strategy

1. **Server tests**
   - Startup payload ordering and protocol shape
   - `daemon.status` / `status.update` separation
   - `/health` remains available and unchanged for readiness

2. **Browser tests**
   - Connection status pill/popover updates from WebSocket state
   - Reconnect behavior under disconnect, visibility change, and pull-to-refresh
   - Debug mode enables browser/client instrumentation

3. **Logging checks**
   - Debug mode emits structured summaries
   - Normal mode stays quiet enough for day-to-day use
   - No unhandled startup message noise in the console

4. **Manual smoke test**
   - Run `alfred --log debug webui --log debug`
   - Open the Web UI, send a message, force a reconnect, and confirm the logs and status UI remain coherent
