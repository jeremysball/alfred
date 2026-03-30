# PRD: Web UI WebSocket and Connection Status Service Cleanup

**GitHub Issue**: [#173](https://github.com/jeremysball/alfred/issues/173)  
**Status**: Draft  
**Priority**: High  
**Created**: 2026-03-30  
**Author**: Agent

---

## 1. Problem Statement

The Web UI transport path is better than it was before PRD #162, but it is still too entangled with page logic.

Today, the client-side WebSocket layer still mixes:
- connection lifecycle
- keepalive behavior
- reconnect policy
- message parsing
- debug instrumentation
- connection status presentation needs
- page lifecycle hooks

That creates five problems:

1. **Transport and app logic are still too close together**
   - The page often needs to understand transport details that should be encapsulated.
   - Transport changes are harder to make safely.

2. **Connection status UI depends on low-level client details**
   - Status surfaces reach into transport internals to build presentation state.
   - That makes connection behavior and UI behavior harder to evolve independently.

3. **Reconnect and keepalive behavior are difficult to reason about**
   - Page visibility, lifecycle hooks, ping/pong, and reconnect policy are all interacting in one area.
   - Bugs can appear as either transport failures or UI inconsistencies.

4. **Refactoring `main.js` is blocked by transport coupling**
   - As long as the page owns too much connection detail, transport and controller cleanup remain entangled.

5. **The app-facing client contract is not yet clean enough**
   - The frontend needs a service boundary that exposes connection and message events cleanly without reintroducing protocol drift.

The result is a transport layer that works, but still exposes too much low-level behavior to the rest of the Web UI.

---

## 2. Goals

1. Create a cleaner **client-facing transport service boundary**.
2. Keep the **existing WebSocket-first message contract** from PRD #162 intact.
3. Separate **connection lifecycle management** from page-level UI concerns.
4. Give the rest of the frontend a stable connection/message interface.
5. Make connection status presentation derive from explicit app-facing state rather than transport internals.
6. Improve testability of reconnect, keepalive, and page lifecycle behavior.

---

## 3. Non-Goals

- Redefining backend WebSocket message semantics from PRD #162.
- Replacing WebSocket with another transport.
- Redesigning the connection status UI.
- Solving all global dependency cleanup inside this PRD.
- Decomposing `main.js` broadly beyond transport-related ownership.

---

## 4. Proposed Solution

### 4.1 Define an app-facing transport contract

Create one app-facing transport service that exposes:
- connection state changes
- incoming message dispatch
- outbound message API
- reconnect events
- transport debug snapshots when needed

The rest of the app should not need to inspect raw client internals directly.

### 4.2 Separate lifecycle policy from presentation

Split responsibilities into clearer layers:
- **transport client**: socket open/close/send/receive
- **lifecycle policy**: keepalive, reconnect, page visibility, page lifecycle behavior
- **connection state surface**: stable app-facing state
- **status presentation/controller**: UI-specific rendering and interaction

### 4.3 Preserve PRD #162 protocol work

This PRD explicitly builds on PRD #162.

Requirements:
- no new protocol drift between frontend and backend
- no fallback back to `/health` for live UI state
- keep message types and debug instrumentation aligned with the server contract

### 4.4 Normalize connection state for the app

The frontend should consume connection state such as:
- `connected`
- `connecting`
- `reconnecting`
- `disconnected`
- last ping/pong information when exposed intentionally
- reconnect attempts when exposed intentionally

That state should be surfaced intentionally rather than inferred ad hoc from socket properties.

### 4.5 Make connection status tooltip/state read from one source

The connection status UI should consume one normalized state surface.

That allows:
- easier controller extraction
- easier tooltip rendering updates
- clearer browser regression tests
- less coupling to transport implementation details

### 4.6 Strengthen test seams around reconnect behavior

High-risk behaviors should be testable through public behavior, including:
- reconnect after disconnect
- visibility/page lifecycle recovery
- keepalive timeout handling
- connection status updates in the UI

---

## 5. Success Criteria

- [ ] The Web UI has one clean app-facing transport service boundary.
- [ ] Connection lifecycle policy is separated from status presentation logic.
- [ ] The rest of the app no longer depends on raw socket internals for normal operation.
- [ ] PRD #162 message contracts remain intact.
- [ ] Reconnect, keepalive, and connection status behavior have targeted regression coverage.
- [ ] The implementation passes the relevant JS and Python validation workflow for touched surfaces.

---

## 6. Milestones

### Milestone 1: Define the transport service contract
Document the client-facing transport API, normalized connection state, and lifecycle ownership boundaries.

Validation: frontend code and tests agree on the app-facing transport contract.

### Milestone 2: Extract transport lifecycle policy
Separate reconnect, keepalive, visibility, and page lifecycle behavior from page-specific presentation code.

Validation: targeted tests prove lifecycle behavior works through the new service boundary.

### Milestone 3: Normalize connection state for app consumption
Expose stable connection-state changes and transport snapshots to the app without requiring direct socket inspection.

Validation: connection status consumers read normalized state instead of transport internals.

### Milestone 4: Migrate status presentation to the normalized state surface
Update connection status UI and related page logic to consume the new app-facing transport state.

Validation: targeted browser tests prove the connection status surface still behaves correctly.

### Milestone 5: Regression coverage and documentation
Add or update tests and docs for reconnect behavior, page lifecycle handling, and normalized connection-state consumption.

Validation: `npm run js:check` passes and targeted browser/WebSocket tests pass for the touched surfaces.

---

## 7. Likely File Changes

```text
src/alfred/interfaces/webui/static/js/websocket-client.js
src/alfred/interfaces/webui/static/js/main.js
src/alfred/interfaces/webui/static/js/app/transport.js         # new or extracted
src/alfred/interfaces/webui/static/js/app/connection-state.js  # possible new
src/alfred/interfaces/webui/static/js/components/status-bar.js # if status integration changes
src/alfred/interfaces/webui/server.py                          # only if testable contract surfaces need alignment

tests/webui/test_websocket.py
tests/webui/test_websocket_client_protocol.py
tests/webui/test_reconnect.py
tests/webui/test_keepalive.py
tests/webui/test_keepalive_browser.py
prds/173-web-ui-websocket-and-connection-status-service-cleanup.md
```

---

## 8. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Transport refactor accidentally changes the server/client contract | High | treat PRD #162 as the protocol source of truth and test against the existing public message contract |
| Connection status UI regresses while internals improve | Medium | migrate presentation only after normalized state exists and protect it with targeted browser tests |
| Lifecycle behavior becomes split across too many modules | Medium | separate by responsibility, not by micro-abstraction |
| Reconnect and visibility bugs remain timing-sensitive | Medium | rely on targeted reconnect/keepalive/public behavior tests instead of internal-only assertions |

---

## 9. Validation Strategy

This PRD touches JavaScript transport code and may also touch Python-backed browser test surfaces.

Required validation depends on touched files:

```bash
npm run js:check
uv run pytest tests/webui/test_websocket.py tests/webui/test_reconnect.py tests/webui/test_keepalive.py tests/webui/test_keepalive_browser.py -v
```

If Python WebSocket server surfaces change, also run the relevant Python workflow for those touched files.

---

## 10. Related PRDs

- PRD #162: Web UI WebSocket-first Status and Debug Instrumentation
- PRD #170: Web UI Bootstrap and Script Loading Cleanup
- PRD #171: Web UI Browser Test Harness and Fixture Stabilization
- PRD #172: Web UI State and Event-Flow Extraction
- PRD #174: main.js Decomposition into Domain Controllers
- PRD #176: Remove Web UI Window Globals and Implicit Dependencies

Series note: PRD #173 should follow the bootstrap and shared state work closely because it provides the transport boundary that later controller cleanup can depend on.

---

## 11. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Build on PRD #162 instead of redefining transport semantics | The current WebSocket-first contract should stay the protocol source of truth |
| 2026-03-30 | Separate lifecycle policy from status presentation | Reconnect/keepalive logic and UI tooltip rendering should not evolve as one unit |
| 2026-03-30 | Expose normalized connection state to the app | Controllers and status surfaces need a stable contract that does not require raw socket inspection |
| 2026-03-30 | Protect reconnect and keepalive behavior with targeted tests | Transport cleanup is too risky to validate by inspection alone |
