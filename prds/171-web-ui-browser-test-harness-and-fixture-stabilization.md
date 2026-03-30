# PRD: Web UI Browser Test Harness and Fixture Stabilization

**GitHub Issue**: [#171](https://github.com/jeremysball/alfred/issues/171)  
**Status**: Draft  
**Priority**: High  
**Created**: 2026-03-30  
**Author**: Agent

---

## 1. Problem Statement

The frontend already has browser-facing tests, but the safety net is not yet clean enough for aggressive refactoring.

Current problems:

1. **Browser regression coverage is broad but uneven**
   - Some important flows are protected.
   - Others still rely on ad hoc setup, custom waits, or duplicated helpers.

2. **Startup and readiness are not deterministic enough in tests**
   - When the page boot contract is implicit, tests need fragile waits and inferred readiness conditions.
   - Refactors become risky because failures can be timing noise instead of meaningful regressions.

3. **Fixtures and fake collaborators need clearer ownership**
   - The repository already has work underway in PRD #139.
   - Frontend refactors still need a stable browser-oriented harness that works with the real startup path and real-shaped backend collaborators.

4. **High-value UI flows need smaller, reusable test seams**
   - Streaming, session load, edit/cancel, keyboard shortcuts, and connection status are all easy to break.
   - It should be cheap to add one focused regression when a new seam is extracted.

5. **Refactor work can outpace verification**
   - Without a stable harness, large cleanup PRDs are tempted to rely on manual testing.
   - That increases regression risk and slows deletion of legacy paths.

The result is a test surface that is useful, but not yet crisp enough to support sustained frontend refactoring in small, confident slices.

---

## 2. Goals

1. Create a **small, deterministic browser regression harness** for Web UI refactors.
2. Make startup/readiness checks **explicit and reusable**.
3. Consolidate shared browser helpers, waits, and test fixtures.
4. Keep tests grounded in **real user-visible behavior** instead of internal implementation details.
5. Make it easy to add targeted regressions for extracted controllers and components.
6. Align browser harness work with PRD #139 instead of duplicating or bypassing it.

---

## 3. Non-Goals

- Replacing all existing Web UI tests with a new framework.
- Converting every browser test into a single mega end-to-end suite.
- Rewriting backend contracts solely for test convenience.
- Making this PRD responsible for the frontend refactor itself.
- Adding visual snapshot testing unless a concrete surface requires it.

---

## 4. Proposed Solution

### 4.1 Define the browser test layers

The Web UI refactor series should use three clear test layers:

1. **Contract tests**
   - startup payloads
   - WebSocket message contracts
   - explicit state and event surfaces

2. **Targeted browser behavior tests**
   - page boot
   - chat send/streaming
   - edit/cancel
   - session load/reconcile
   - connection status interactions
   - keyboard and command surfaces

3. **Feature smoke tests**
   - optional browser features that need one proof they still boot and attach correctly

### 4.2 Add deterministic readiness helpers

Tests need a stable way to know when the app is actually ready.

Requirements:
- one explicit browser-readable readiness seam
- reusable helper functions for “page booted” and “feature initialized” checks
- consistent waits for streaming and async UI updates
- reduced dependence on arbitrary sleeps

### 4.3 Consolidate shared fixtures and helpers

Create or refine shared helpers for:
- Web UI page startup
- browser connection setup
- WebSocket message injection or observation
- fake or real-shaped collaborators
- common chat/session actions
- reusable assertions for streaming and status surfaces

### 4.4 Test through public behavior

When a refactor touches browser-visible behavior, tests should exercise:
- the real page
- the public command or WebSocket path
- the actual DOM behavior users rely on

They should avoid depending on private implementation details where a public behavior assertion would be stronger.

### 4.5 Make regressions cheap to add

Each extracted seam in the refactor series should be able to add one targeted regression with minimal setup.

Examples:
- one startup test for bootstrap extraction
- one connection-state test for WebSocket cleanup
- one message-rendering test for `chat-message` decomposition
- one controller-level browser test for `main.js` extraction

### 4.6 Keep fixture realism aligned with PRD #139

This PRD should not introduce new mock-heavy browser shims that fight PRD #139.

Instead:
- prefer explicit fakes
- prefer public contracts
- keep helpers small and composable
- use realistic startup paths rather than bypassing the app entirely

---

## 5. Success Criteria

- [ ] Browser tests can wait on one deterministic app-ready seam.
- [ ] Shared Web UI test helpers remove duplicated startup and interaction logic.
- [ ] High-risk refactor surfaces have targeted browser regressions.
- [ ] Frontend refactors can land in smaller slices with meaningful browser validation.
- [ ] Browser fixtures stay aligned with real-shaped collaborator rules from PRD #139.
- [ ] The implementation passes the relevant Python and JS validation workflow for touched surfaces.

---

## 6. Milestones

### Milestone 1: Define the browser harness contract
Document the browser test layers, startup readiness contract, and fixture rules for frontend refactors.

Validation: test helpers and docs agree on how readiness and shared setup should work.

### Milestone 2: Consolidate shared startup and interaction helpers
Add or refine shared utilities for page boot, readiness waits, common chat actions, and repeated Web UI assertions.

Validation: targeted tests use the shared helpers instead of duplicating boot/setup logic.

### Milestone 3: Stabilize high-risk browser regressions
Protect the most refactor-sensitive flows with deterministic targeted tests.

Validation: targeted browser tests cover boot, chat streaming, session load, edit/cancel, and connection status behavior.

### Milestone 4: Align fixture realism with frontend refactor needs
Update browser-facing fixtures and fakes so they match real contracts closely enough for controller and component cleanup work.

Validation: touched tests use explicit fakes or realistic collaborators instead of broad MagicMock-style shortcuts.

### Milestone 5: Regression coverage and documentation
Document the harness expectations and add the browser regression entry points needed for PRDs #170-#176.

Validation: relevant targeted Web UI tests pass consistently and the harness is usable by the rest of the refactor series.

---

## 7. Likely File Changes

```text
tests/webui/conftest.py
tests/webui/fakes.py
tests/webui/test_bootstrap.py
tests/webui/test_frontend.py
tests/webui/test_websocket.py
tests/webui/test_streaming_composer.py
tests/webui/test_streaming_edit.py
tests/webui/test_sessions.py
tests/webui/test_reconnect.py
tests/webui/test_server_parity.py
# plus new shared helpers or focused browser regression files as needed

src/alfred/interfaces/webui/static/js/...          # only if readiness/debug hooks need explicit surfacing
prds/171-web-ui-browser-test-harness-and-fixture-stabilization.md
```

---

## 8. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Test harness work turns into a full testing-program rewrite | Medium | keep scope limited to frontend refactor safety and deterministic browser seams |
| New helpers hide real behavior behind too much abstraction | Medium | test through public page behavior and keep helpers narrow |
| Timing flakiness remains after refactor | High | add explicit readiness and event completion seams instead of sleep-heavy waits |
| Fixture work conflicts with PRD #139 | Medium | treat PRD #139 as the contract source for fake realism and avoid mock-heavy new shims |

---

## 9. Validation Strategy

This PRD is primarily Python-led because most browser verification lives under `tests/webui/`.

Required validation depends on touched files:

```bash
uv run ruff check src/
uv run mypy --strict src/
uv run pytest tests/webui/test_bootstrap.py tests/webui/test_frontend.py tests/webui/test_websocket.py -v
```

If JavaScript helpers or browser-exposed readiness seams change, also run:

```bash
npm run js:check
```

---

## 10. Related PRDs

- PRD #139: Web UI Test Fixture Realism
- PRD #165: Selective Tool Outcomes and Context Viewer Fixes
- PRD #170: Web UI Bootstrap and Script Loading Cleanup
- PRD #172: Web UI State and Event-Flow Extraction
- PRD #173: Web UI WebSocket and Connection Status Service Cleanup
- PRD #174: main.js Decomposition into Domain Controllers
- PRD #175: Chat Message Component Decomposition

Series note: PRD #171 should land before or alongside the major structural refactor PRDs so they have a stable browser safety net.

---

## 11. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Protect the refactor with targeted browser regressions early | Cleanup work is safer when failures point to real behavior instead of timing noise |
| 2026-03-30 | Use explicit readiness seams instead of sleep-heavy waits | Browser tests need deterministic startup and async boundaries |
| 2026-03-30 | Keep fixture realism aligned with PRD #139 | The refactor should not reintroduce mock-shaped browser shortcuts |
| 2026-03-30 | Prefer small reusable helpers over test-specific boot code | Refactor slices need cheap, repeatable validation |
