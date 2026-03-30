# PRD: Web UI State and Event-Flow Extraction

**GitHub Issue**: [#172](https://github.com/jeremysball/alfred/issues/172)  
**Status**: Draft  
**Priority**: High  
**Created**: 2026-03-30  
**Author**: Agent

---

## 1. Problem Statement

The Web UI still manages too much runtime behavior through direct DOM mutation and cross-cutting imperative logic.

Today, core behavior such as:
- session loading
- streaming assistant output
- composer mode
- edit/cancel flows
- message queueing
- connection status
- tool-call tracking

is updated from many places at once.

That creates six problems:

1. **There is no clear source of truth for runtime UI state**
   - Session identity, current streaming message, queue contents, and composer mode can all be inferred from several places.
   - That makes it harder to reason about correctness.

2. **Message handling and UI rendering are too tightly coupled**
   - WebSocket messages often mutate UI directly.
   - That makes it hard to separate transport, state transitions, and rendering ownership.

3. **Cross-feature behavior is harder to test**
   - Editing, canceling, retrying, and loading sessions all interact.
   - Without explicit state transitions, tests have to infer correctness from final DOM alone.

4. **Refactoring creates hidden regressions**
   - When behavior depends on scattered mutation, moving one block can break another flow without obvious boundaries.

5. **Feature modules have no stable runtime contract to integrate with**
   - Keyboard shortcuts, connection status, notifications, and optional features often depend on whatever state happens to exist in the page.

6. **`main.js` stays large because it owns both orchestration and state**
   - Decomposition is much harder before state ownership is extracted.

The result is a Web UI that behaves correctly through accumulated imperative logic rather than a small, explicit application model.

---

## 2. Goals

1. Create one **small application state layer** for the Web UI.
2. Make key runtime transitions **explicit and testable**.
3. Separate **events**, **state transitions**, and **rendering/application** concerns.
4. Give controllers and components one stable integration contract.
5. Keep the solution lightweight and framework-free.
6. Create a foundation for PRDs #173-#176.

---

## 3. Non-Goals

- Introducing Redux, Zustand, or another heavyweight state framework.
- Rewriting the backend protocol.
- Redesigning the UI or changing core product behavior.
- Decomposing every component in this PRD.
- Making optional feature state first-class unless the core runtime depends on it.

---

## 4. Proposed Solution

### 4.1 Add a lightweight app state model

Create one explicit app-owned state surface for the core runtime.

Likely domains:
- `session`
- `composer`
- `streaming`
- `messages`
- `queue`
- `connection`
- `toolCalls`
- `ui` for shared top-level status when needed

The state model should be small, explicit, and easy to inspect.

### 4.2 Route behavior through events and transitions

Core browser behavior should be expressed as:
1. event occurs
2. state transition is applied
3. UI controllers or components react to the new state

Examples:
- `chat.started`
- `chat.chunk`
- `chat.complete`
- `chat.cancelled`
- `session.loaded`
- `composer.edit_started`
- `connection.changed`

The goal is not to create ceremony. The goal is to make interactions predictable.

### 4.3 Separate transport from app state

WebSocket messages should not directly own DOM mutation.

Instead:
- transport receives message
- message is normalized into app events
- state updates occur
- controllers/components render the consequence

This aligns with PRD #173 and makes `main.js` decomposition safer.

### 4.4 Keep rendering ownership local

The state layer should not become a second UI system.

Requirements:
- state holds runtime truth
- controllers translate state into page updates
- components continue to own their own rendering internals
- state should not mirror every DOM detail

### 4.5 Define the core state contract first

The first extracted state layer should cover the highest-risk flows:
- active session identity
- current assistant stream state
- current editable message state
- queued outbound messages
- connection state
- active tool-call state for the current turn

Optional feature state can remain local until it needs the shared runtime model.

### 4.6 Preserve incremental migration

This PRD should support a move-then-delete approach:
1. define app state contract
2. migrate one runtime domain at a time
3. delete the old imperative path as soon as the new one is authoritative

No long-lived dual path should remain.

---

## 5. Success Criteria

- [ ] Web UI has one small explicit app state layer for core runtime behavior.
- [ ] High-risk flows use explicit state transitions instead of scattered mutation alone.
- [ ] WebSocket handling and UI application are separated by a stable event/state boundary.
- [ ] Controllers and components can integrate against the same runtime contract.
- [ ] The implementation stays framework-free and lightweight.
- [ ] The implementation passes the relevant JS and browser validation workflow.

---

## 6. Milestones

### Milestone 1: Define the app state contract
Document the minimal runtime domains, event vocabulary, and ownership rules for the shared state layer.

Validation: docs and tests agree on the core state shape and the highest-risk transitions.

### Milestone 2: Extract core runtime state
Implement the shared state layer for session, streaming, composer, queue, connection, and active tool-call behavior.

Validation: targeted tests prove the state layer can represent the core runtime flows without relying on DOM inspection alone.

### Milestone 3: Route WebSocket and UI actions through explicit transitions
Map incoming transport messages and key user actions into explicit events and state transitions.

Validation: targeted browser and JS tests prove chat, session load, edit/cancel, and queue behavior follow the new event/state path.

### Milestone 4: Delete legacy scattered state paths
Remove old imperative state duplication once the new shared state is authoritative.

Validation: touched flows no longer depend on parallel state bookkeeping in `main.js`.

### Milestone 5: Regression coverage and documentation
Add or update tests and documentation for the core runtime state model and event-flow contract.

Validation: `npm run js:check` passes and targeted Web UI/browser tests pass for the touched flows.

---

## 7. Likely File Changes

```text
src/alfred/interfaces/webui/static/js/main.js
src/alfred/interfaces/webui/static/js/app/state.js            # new
src/alfred/interfaces/webui/static/js/app/events.js           # possible new
src/alfred/interfaces/webui/static/js/app/store.js            # possible new
src/alfred/interfaces/webui/static/js/websocket-client.js     # if event handoff is added
src/alfred/interfaces/webui/static/js/components/...          # if components consume explicit state inputs

tests/webui/test_frontend.py
tests/webui/test_websocket.py
tests/webui/test_streaming_composer.py
tests/webui/test_streaming_edit.py
tests/webui/test_sessions.py
prds/172-web-ui-state-and-event-flow-extraction.md
```

---

## 8. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The state layer becomes over-engineered | Medium | keep the contract small and focused on core runtime truth only |
| DOM state and app state drift apart during migration | High | migrate one domain at a time and delete the old path immediately after the new one is authoritative |
| Event naming becomes vague or inconsistent | Medium | define a small explicit vocabulary and test the highest-risk transitions |
| Optional features force premature complexity into the store | Medium | keep auxiliary state local until it truly needs shared runtime ownership |

---

## 9. Validation Strategy

This PRD is primarily JavaScript with browser-visible behavior.

Required validation depends on touched files:

```bash
npm run js:check
uv run pytest tests/webui/test_frontend.py tests/webui/test_websocket.py tests/webui/test_streaming_composer.py tests/webui/test_streaming_edit.py -v
```

If Python-backed WebSocket or server surfaces change, also run the relevant Python workflow for the touched files.

---

## 10. Related PRDs

- PRD #170: Web UI Bootstrap and Script Loading Cleanup
- PRD #171: Web UI Browser Test Harness and Fixture Stabilization
- PRD #173: Web UI WebSocket and Connection Status Service Cleanup
- PRD #174: main.js Decomposition into Domain Controllers
- PRD #175: Chat Message Component Decomposition
- PRD #176: Remove Web UI Window Globals and Implicit Dependencies

Series note: PRD #172 should follow bootstrap stabilization and provide the state contract that later controller and dependency cleanup work builds on.

---

## 11. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Use a lightweight app-owned state layer | The frontend needs explicit runtime truth without adopting a heavy framework |
| 2026-03-30 | Separate events, state transitions, and rendering | Refactors are safer when transport and DOM updates stop mutating each other directly |
| 2026-03-30 | Limit shared state to core runtime domains first | The first goal is correctness in chat/session/composer behavior, not full app modeling |
| 2026-03-30 | Delete old imperative state paths as soon as possible | Long-lived dual paths make correctness worse, not better |
