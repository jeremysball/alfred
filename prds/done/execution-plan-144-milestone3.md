# Execution Plan: PRD #144 - Milestone 3

## Overview

Add structured core lifecycle logging so a single Alfred turn explains itself from entry through context assembly, agent execution, and completion/failure. This phase assumes the separate root vs Web UI logging split is already in place and focuses on the Alfred runtime path.

**Current Phase:** Milestone 3 - Core turn and context lifecycle

---

## Milestone 3: Core turn and context lifecycle

### 3.1 Successful turn lifecycle logs

- [ ] **Test**: `test_chat_stream_logs_core_turn_lifecycle_on_success()`
  - Create `tests/test_core_observability.py`
  - Use explicit fakes for the context loader, agent, and session manager so the test exercises the real `Alfred.chat_stream()` path without root-level `MagicMock` drift
  - Run a successful streamed turn with a few chunks and assert the log stream includes:
    - `core.turn.start`
    - `core.context.start` / `core.context.completed`
    - `core.agent_loop.start` / `core.agent_loop.completed`
    - `core.turn.completed`
  - Assert the logs carry metadata such as duration, message length, and response size rather than full content
- [ ] **Implement**: add a shared turn lifecycle wrapper in `src/alfred/alfred.py`
  - Emit success-path logs around both `chat_stream()` and `chat()`
  - Track a turn identifier, duration, and lightweight metadata
  - Keep the logs concise and metadata-oriented
- [ ] **Run**: `uv run pytest tests/test_core_observability.py::test_chat_stream_logs_core_turn_lifecycle_on_success -v`

### 3.2 Failed turn lifecycle logs

- [ ] **Test**: `test_chat_stream_logs_core_turn_failed_when_agent_raises()`
  - Reuse `tests/test_core_observability.py`
  - Force the agent or context loader to raise a controlled exception
  - Assert the log stream includes `core.turn.failed` with a failure category/boundary and duration
- [ ] **Implement**: extend the turn lifecycle wrapper in `src/alfred/alfred.py`
  - Catch non-cancellation exceptions
  - Emit a single failure log with enough metadata to identify the failing boundary
  - Preserve the original exception behavior
- [ ] **Run**: `uv run pytest tests/test_core_observability.py::test_chat_stream_logs_core_turn_failed_when_agent_raises -v`

### 3.3 Cancelled turn lifecycle logs

- [ ] **Test**: `test_chat_stream_logs_core_turn_cancelled_when_task_is_cancelled()`
  - Reuse `tests/test_core_observability.py`
  - Cancel the running turn task mid-stream using a deterministic fake that blocks until cancellation
  - Assert the log stream includes `core.turn.cancelled` and still records duration
- [ ] **Implement**: handle `asyncio.CancelledError` in the turn lifecycle wrapper in `src/alfred/alfred.py`
  - Log cancellation distinctly from generic failures
  - Ensure cleanup and persistence behavior stay correct
- [ ] **Run**: `uv run pytest tests/test_core_observability.py::test_chat_stream_logs_core_turn_cancelled_when_task_is_cancelled -v`

### 3.4 Context assembly summary logs

- [ ] **Test**: `test_context_builder_logs_assembly_summary_and_budget_usage()`
  - Create `tests/test_context_observability.py`
  - Exercise `ContextBuilder.build_context()` or `ContextLoader.assemble_with_search()` with a fake store and deterministic session messages
  - Assert logs include `core.context.start` / `core.context.completed` and summary metadata such as memory count, session-message count, and budget information
- [ ] **Implement**: add context assembly logs in `src/alfred/context.py`
  - Emit start/end logs around memory search and context assembly
  - Include result counts, token-budget summary, and timing
- [ ] **Run**: `uv run pytest tests/test_context_observability.py::test_context_builder_logs_assembly_summary_and_budget_usage -v`

### 3.5 Context truncation diagnostics

- [ ] **Test**: `test_context_builder_logs_truncation_when_budget_is_exceeded()`
  - Reuse `tests/test_context_observability.py`
  - Force the budget path with an intentionally small memory budget and enough content to trim
  - Assert the log stream includes `core.context.truncated` with before/after counts
- [ ] **Implement**: log the budget-overflow path in `src/alfred/context.py`
  - Keep the existing truncation behavior
  - Add a concise warning that identifies why and how the context was trimmed
- [ ] **Run**: `uv run pytest tests/test_context_observability.py::test_context_builder_logs_truncation_when_budget_is_exceeded -v`

---

## Files to Modify

1. `src/alfred/alfred.py` - core turn and agent-loop lifecycle logs
2. `src/alfred/context.py` - context assembly, search summary, and truncation logs
3. `tests/test_core_observability.py` - new turn lifecycle behavior tests
4. `tests/test_context_observability.py` - new context lifecycle behavior tests

## Verification Commands

```bash
uv run pytest tests/test_core_observability.py tests/test_context_observability.py -q
uv run ruff check src/ tests/
uv run mypy --strict src/
uv run pytest -m "not slow"
uv run alfred --log debug
```

## Commit Strategy

Suggested atomic commits:
- `test(core): cover successful turn lifecycle logging`
- `fix(core): log successful turn lifecycle boundaries`
- `test(core): cover failed turn lifecycle logging`
- `fix(core): log failed turn lifecycle boundaries`
- `test(core): cover cancelled turn lifecycle logging`
- `fix(core): log cancelled turn lifecycle boundaries`
- `test(context): cover context assembly logging`
- `fix(context): log context assembly summaries`
- `test(context): cover context truncation diagnostics`
- `fix(context): log context truncation`

## Next Task

- [ ] **Test**: `test_chat_stream_logs_core_turn_lifecycle_on_success()`
- [ ] **Implement**: add a shared turn lifecycle wrapper in `src/alfred/alfred.py`
- [ ] **Run**: `uv run pytest tests/test_core_observability.py::test_chat_stream_logs_core_turn_lifecycle_on_success -v`
