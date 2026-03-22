# Execution Plan: PRD #144 - Milestone 5

## Overview

Surface the tool and storage boundaries so slow, broken, or noisy turns can be localized without guessing. Core turn and LLM lifecycle logging are already covered; this phase makes tool execution and persistence/search paths equally explicit and testable.

**Current Phase:** Milestone 5 - Tool and storage surfaces

---

## Milestone 5: Tool and storage surfaces

### 5.1 Tool execution lifecycle logs

- [ ] **Test**: `test_execute_tool_with_events_logs_tool_lifecycle_metadata()`
  - Extend `tests/test_agent_run_stream.py` or create a focused `tests/test_agent_observability.py`
  - Exercise `Agent._execute_tool_with_events()` with a streaming tool that yields multiple chunks
  - Assert the log stream includes `tools.tool.start` and `tools.tool.completed`
  - Verify lifecycle metadata includes `tool_call_id`, `tool_name`, `argument_count`, `argument_keys`, `chunks`, `output_chars`, `is_error`, and `duration_ms`
- [ ] **Implement**: tighten `src/alfred/agent.py`
  - Keep tool logs metadata-first and concise
  - Preserve the same lifecycle envelope on success and failure paths
  - Avoid logging full tool inputs or outputs unless already justified by the code path
- [ ] **Run**: `uv run pytest tests/test_agent_run_stream.py -v`

### 5.2 Tool failure boundaries stay visible

- [ ] **Test**: `test_execute_tool_with_events_logs_tool_failure_boundary()`
  - Reuse the same agent test file
  - Force a tool generator to raise after emitting at least one chunk
  - Assert the lifecycle still ends with `tools.tool.completed` and failure metadata
- [ ] **Implement**: keep `src/alfred/agent.py` failure handling aligned with the success-path envelope
  - Ensure the end event is emitted even when a tool raises
  - Keep the failure signal explicit but compact
- [ ] **Run**: `uv run pytest tests/test_agent_run_stream.py -v -k 'tool_failure_boundary or execute_tool_error'`

### 5.3 Storage persistence and search boundaries log clearly

- [ ] **Test**: `test_sqlite_store_logs_search_and_persistence_boundaries()`
  - Extend `tests/storage/test_storage_observability.py` and, if needed, `tests/storage/test_sqlite_similarity_semantics.py`
  - Cover `save_session`, `save_summary`, `session_summary_search`, and `session_message_search`
  - Assert `storage.session_save.*`, `storage.session_summary_save.*`, `storage.session_summary_search.*`, and `storage.session_message_search.*` include duration/count metadata and explicit failure paths where applicable
- [ ] **Implement**: align `src/alfred/storage/sqlite.py`
  - Keep storage event naming consistent across write and search paths
  - Make slow/failing boundaries obvious in debug logs
  - Prefer counts, identifiers, and durations over content dumps
- [ ] **Run**: `uv run pytest tests/storage/test_storage_observability.py tests/storage/test_sqlite_similarity_semantics.py -v`

---

## Files to Modify

1. `src/alfred/agent.py` - tool lifecycle logging and failure envelope consistency
2. `src/alfred/storage/sqlite.py` - persistence/search lifecycle logging
3. `tests/test_agent_run_stream.py` - tool lifecycle regression coverage
4. `tests/storage/test_storage_observability.py` - persistence lifecycle regression coverage
5. `tests/storage/test_sqlite_similarity_semantics.py` - search lifecycle regression coverage

## Verification Commands

```bash
uv run pytest tests/test_agent_run_stream.py tests/storage/test_storage_observability.py tests/storage/test_sqlite_similarity_semantics.py -q
uv run ruff check src/ tests/
uv run mypy --strict src/
uv run pytest -m "not slow"
```

## Commit Strategy

Suggested atomic commits:
- `test(agent): cover tool lifecycle logging`
- `fix(agent): align tool lifecycle metadata`
- `test(storage): cover persistence and search logging`
- `fix(storage): align persistence and search metadata`

## Next Task

- [ ] **Test**: `test_execute_tool_with_events_logs_tool_lifecycle_metadata()`
- [ ] **Implement**: tighten `src/alfred/agent.py`
- [ ] **Run**: `uv run pytest tests/test_agent_run_stream.py -v`
