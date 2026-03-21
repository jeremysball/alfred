# PRD: Web UI Test Fixture Realism

**GitHub Issue**: [#139](https://github.com/jeremysball/alfred/issues/139)  
**Status**: Complete  
**Priority**: Medium  
**Created**: 2026-03-21  
**Completed**: 2026-03-21

---

## 1. Problem Statement

Several Web UI tests still rely on unrealistic test doubles. The most obvious example is the bare, root-level `MagicMock`, but that is only part of the problem.

The deeper problem is that some Web UI tests still use legacy Alfred shapes that do not match the production Web UI API. Production code has adapted to those fixtures. `src/alfred/interfaces/webui/server.py` now contains compatibility branches for:
- `MagicMock`-specific fixture handling
- root-level session APIs such as `new_session`, `resume_session`, `list_sessions`, and `current_session`
- legacy `/context` access through `alfred.get_context()`
- startup gating based on fixture-only shapes such as a dict-like `config`

Those branches make tests less realistic and let contract drift hide in plain sight. The server can tolerate missing or wrong interfaces instead of failing when the Web UI contract changes.

This PRD fixes that by defining the real Web UI-facing contract, moving tests onto explicit fakes that match that contract, and deleting test-only compatibility logic from production code.

Realism here means two things:
1. **Fixture realism** — test doubles match the real object shape the server uses.
2. **Interaction realism** — public Web UI behavior is verified through the WebSocket interface whenever practical, not only through private helper calls.

---

## 2. Goals & Success Criteria

### Goals
1. Define a small, explicit Web UI contract around the modern Alfred API.
2. Replace bare root-level `MagicMock` and legacy Alfred fixtures with Protocol-backed fakes that use real production data models.
3. Remove all test-only and legacy-fixture compatibility branches from the Web UI server.
4. Keep WebSocket behavior tests as the primary verification path for chat, sessions, context, status, and tool calls.
5. Make contract drift fail fast and clearly.

### Success Criteria
- [x] `src/alfred/interfaces/webui/server.py` no longer imports or branches on `MagicMock`.
- [x] The Web UI server no longer falls back to root-level `new_session`, `resume_session`, `list_sessions`, `current_session`, or `get_context` APIs.
- [x] The Web UI server no longer skips normal startup behavior because a fixture uses a dict-shaped `config` or other legacy-only object shape.
- [x] The Web UI contract is defined explicitly with Protocols: `WebUISessionManager`, `WebUICore`, and `WebUIAlfred`.
- [x] Shared Web UI fakes live in `tests/webui/fakes.py`.
- [x] The shared fake harness uses real production data models where possible: `Session`, `SessionMeta`, `Message`, `ToolCallRecord`, and `TokenTracker`.
- [x] `tests/webui/` contains no bare top-level `MagicMock` Alfred fixture.
- [x] `tests/webui/test_server_parity.py` covers startup, `/new`, `/resume`, `/sessions`, `/session`, and `/context` against the modern contract.
- [x] Chat, session, and tool-call flows are verified through WebSocket tests; direct private-helper tests remain only for narrow batching or parsing logic.
- [x] `uv run pytest tests/webui -q --timeout=30` passes.
- [x] `uv run alfred webui --port 8080` launches successfully after the refactor.
- [x] A browser-level smoke check passes for Web UI startup and connection behavior.

---

## 3. Proposed Solution

### 3.1 Define the Web UI contract with Protocols

The Web UI server does not need the full Alfred object. It needs a small, typed slice of it. Define that slice explicitly with Protocols.

Recommended Protocols:

```python
from collections.abc import AsyncIterator, Callable
from typing import Protocol

from alfred.agent import ToolEvent
from alfred.session import Session, SessionMeta
from alfred.token_tracker import TokenTracker


class WebUISessionManager(Protocol):
    async def new_session_async(self) -> Session: ...
    async def resume_session_async(self, session_id: str) -> Session: ...
    async def list_sessions_async(self) -> list[SessionMeta]: ...
    def get_current_cli_session(self) -> Session | None: ...
    def start_session(self) -> Session: ...


class WebUICore(Protocol):
    session_manager: WebUISessionManager


class WebUIAlfred(Protocol):
    core: WebUICore
    token_tracker: TokenTracker
    model_name: str

    async def chat_stream(
        self,
        message: str,
        tool_callback: Callable[[ToolEvent], None] | None = None,
    ) -> AsyncIterator[str]: ...

    def sync_token_tracker_from_session(
        self,
        session_id: str | None = None,
    ) -> None: ...
```

These Protocols describe the exact surface the Web UI server is allowed to depend on. They are a narrow contract, not a second object model.

### 3.2 Use real production data models for session, message, and token state

Do not create parallel fake copies of simple production dataclasses.

Use real production types for:
- `Session`
- `SessionMeta`
- `Message`
- `ToolCallRecord`
- `TokenTracker`

Only fake the behavioral seams that need controllable test behavior:
- `SessionManager`
- the thin top-level Alfred wrapper
- boundary spies such as websocket send assertions or patched helper calls

This keeps the tests close to production and removes one more place where API drift can hide.

### 3.3 Add a shared fake harness in `tests/webui/fakes.py`

Create a small, explicit test harness for Web UI tests.

Recommended contents:
- `FakeSessionManager` implementing `WebUISessionManager`
- `FakeCore`
- `FakeAlfred` implementing `WebUIAlfred`
- small helper constructors such as `make_session()`, `make_message()`, and `make_tool_call()` that build real production dataclasses

Guidelines:
- Keep the file small and readable.
- Prefer direct dataclass construction over a builder DSL.
- Add helper functions only when they remove real duplication.
- Keep the harness local to `tests/webui/`; do not generalize it for the rest of the test suite in this PRD.

### 3.4 Keep mocks at the edges only

`MagicMock`, `AsyncMock`, and similar tools still have a place. Use them only at the boundary:
- websocket spies
- one-off leaf assertions
- patching shared helpers such as `alfred.context_display.get_context_display`

Do not use a bare root-level mock that can impersonate the entire Alfred tree.

### 3.5 Remove all test-only and legacy-fixture compatibility branches from production code

Once the tests use the modern contract, delete the server-side fallbacks that exist only to support unrealistic fixtures.

That includes removing support for:
- `MagicMock` checks in `server.py`
- root-level Alfred fallbacks in `_create_session()`, `_resume_session()`, `_list_sessions()`, and `_get_current_session()`
- legacy `/context` fallback through `alfred.get_context()`
- startup gating based on fixture-only shapes such as dict `config`

After this change, the Web UI server should do one of two things:
- operate against the modern Web UI contract, or
- fail clearly when required contract members are missing

### 3.6 Prefer public-interface behavior tests over private-helper tests

For Web UI behavior, the default test path should be the real WebSocket interface.

Use WebSocket tests for:
- startup connection behavior
- chat streaming
- session commands
- status updates
- tool-call event flow
- `/context`

Direct tests of private helpers such as `_handle_chat_message()` are still acceptable, but only for narrow internal behavior that is awkward to isolate through the full WebSocket stack, such as:
- chunk batching
- reasoning marker parsing
- precise tool-event emission order

The public interface should remain the main source of truth.

---

## 4. Technical Implementation

### Likely file changes

```text
src/alfred/interfaces/webui/contracts.py      # new Protocol definitions
src/alfred/interfaces/webui/server.py         # remove test-only / legacy shims

tests/webui/fakes.py                          # shared Web UI fake harness
tests/webui/test_server_parity.py             # expand contract and parity coverage
tests/webui/test_chat.py                      # migrate away from root-level MagicMock
tests/webui/test_integration.py               # migrate from legacy Alfred shape
tests/webui/test_websocket.py                 # migrate to shared fake harness
tests/webui/test_tool_calls.py                # keep helper tests narrow and explicit
tests/webui/test_browser_smoke.py             # add if no existing browser smoke covers startup
```

### Contract details

The fake Alfred/session objects should cover the behaviors the server actually exercises:
- session creation and resumption through `core.session_manager`
- session listing and current-session lookup through `core.session_manager`
- token tracker synchronization via `sync_token_tracker_from_session(...)`
- model name and token totals for status updates
- chat streaming with optional tool callback support

### `/context` guidance

The Web UI server should call the shared `get_context_display()` implementation directly. Tests for `/context` should patch that shared helper at the boundary when they do not need the full Alfred context-loading stack.

Do not preserve `alfred.get_context()` as a fallback API just to satisfy tests.

### Avoid
- fake copies of `Session`, `SessionMeta`, `Message`, `ToolCallRecord`, or `TokenTracker`
- root-level `MagicMock` objects that impersonate the full Alfred tree
- production code that branches on test-double types
- fixture-driven startup branches that bypass normal server behavior
- builder-style test DSLs that hide the real session/message shape

---

## 5. Milestones

### Milestone 0: Codify the modern Web UI contract with failing tests
Expand `tests/webui/test_server_parity.py` first so the desired contract is explicit before refactoring production code.

Required coverage:
- connection startup
- `/new`
- `/resume`
- `/sessions`
- `/session`
- `/context`
- status synchronization on connect and resume

### Milestone 1: Add Protocols and the shared fake harness
Create `contracts.py` and `tests/webui/fakes.py`.

Use real production dataclasses for session, message, tool-call, and token state.

### Milestone 2: Migrate startup and session-command tests
Move tests off legacy Alfred shapes and onto `FakeAlfred` + `FakeSessionManager` using the modern `core.session_manager` path.

### Milestone 3: Migrate chat and tool-call tests
Update chat and tool-call coverage to use the shared harness and prefer WebSocket-driven behavior tests.

Keep direct helper tests only where they provide focused coverage for batching or parsing internals.

### Milestone 4: Remove production compatibility branches
Delete all Web UI server paths that exist only for `MagicMock`, legacy root-level Alfred methods, legacy `get_context()`, or fixture-only startup shapes.

### Milestone 5: Stabilize the full Web UI suite and smoke checks
Run the full Web UI suite, fix expectation mismatches, and verify the refactored server still launches and connects correctly.

### Milestone 6: Document the fixture contract and guardrails
Add a short note in `tests/webui/fakes.py` or nearby test docs explaining:
- the Protocols
- the real data models in use
- when mocks are still acceptable
- why bare root-level `MagicMock` is forbidden here

---

## 6. Validation Strategy

### Required checks
- `uv run pytest tests/webui/test_server_parity.py -q --timeout=30`
- `uv run pytest tests/webui/test_chat.py -q --timeout=30`
- `uv run pytest tests/webui/test_integration.py -q --timeout=30`
- `uv run pytest tests/webui/test_websocket.py -q --timeout=30`
- `uv run pytest tests/webui/test_tool_calls.py -q --timeout=30`
- `uv run pytest tests/webui -q --timeout=30`
- `uv run ruff check src/ tests/webui/`
- `uv run mypy --strict src/`
- `uv run alfred webui --port 8080`
- Run one browser-level smoke check against the Web UI. If no generic smoke test exists yet, add one in `tests/webui/test_browser_smoke.py`.

### What success looks like
- The server depends only on the modern Web UI contract.
- Shared fakes are small, obvious, and use real production data models.
- Missing contract members fail quickly instead of being silently invented by a mock.
- Public WebSocket behavior remains covered end to end.
- The full Web UI suite passes without test-only server shims.
- The app starts and a browser can connect successfully.

---

## 7. Risks & Mitigations

### Risk: The Protocols become too broad
**Mitigation:** keep each Protocol limited to what `server.py` actually uses. Do not turn the Protocols into a second full Alfred API.

### Risk: The fake harness becomes a second compatibility layer
**Mitigation:** use real production dataclasses, keep helpers thin, and avoid convenience shims that hide missing fields or wrong shapes.

### Risk: Some tests still depend on legacy helper paths
**Mitigation:** migrate from parity tests outward. Remove compatibility branches only after the new tests pass against the modern contract.

### Risk: Public-interface tests become verbose
**Mitigation:** keep a small number of focused direct-helper tests for batching and parsing internals, but move feature behavior checks to WebSocket tests.

### Risk: `/context` tests become awkward without legacy fallback
**Mitigation:** patch `get_context_display()` at the boundary when needed. Do not reintroduce `alfred.get_context()`.

---

## 8. Non-Goals

- No Web UI feature redesign.
- No changes to the WebSocket message format.
- No global ban on `MagicMock` across the full repository.
- No extraction of a cross-project fake harness for non-Web UI tests.
- No builder-style test DSL for sessions or messages.
- No new end-user functionality.

---

## 9. Resolved Design Decisions

1. **Protocols to define the contract**: use `WebUISessionManager`, `WebUICore`, and `WebUIAlfred`.
2. **Shared fake harness location**: place it in `tests/webui/fakes.py`.
3. **Real data models over fake copies**: use `Session`, `SessionMeta`, `Message`, `ToolCallRecord`, and `TokenTracker` directly.
4. **Mocks only at the edges**: keep `MagicMock` and `AsyncMock` for websocket spies, patched helper calls, and other isolated leaf dependencies.
5. **Scope of the cleanup**: remove all Web UI test-only and legacy-fixture compatibility branches, not just `MagicMock` checks.
6. **Test style**: prefer WebSocket behavior tests; keep direct helper tests only for narrow internal logic.
7. **Test data construction**: prefer real constructors and small helper functions; do not add a builder API or DSL.
8. **Harness scope**: keep the shared fake harness local to `tests/webui/` unless a future PRD justifies broader reuse.

---

## 10. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-21 | Define a formal Web UI contract with Protocols | The server needs a small, explicit interface slice, not the full Alfred object |
| 2026-03-21 | Use real production dataclasses for session, message, tool-call, and token state | Duplicate fake data models would create a second drifting contract |
| 2026-03-21 | Remove all test-only and legacy-fixture branches from `server.py` | Production code should reflect the real API, not old tests |
| 2026-03-21 | Center the refactor on parity tests and WebSocket behavior tests | Realism requires both realistic fixture shape and realistic interaction paths |
| 2026-03-21 | Keep the shared fake harness in `tests/webui/fakes.py` with no builder DSL | A small local harness is easier to read, harder to misuse, and less likely to grow into abstraction creep |
