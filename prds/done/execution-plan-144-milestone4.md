# Execution Plan: PRD #144 - Milestone 4

## Overview

LLM lifecycle observability is already partially in place in `src/alfred/llm.py` and `tests/test_llm_observability.py`. This phase closes the gaps by covering the non-streaming request path and the retry/failure edges so the request lifecycle is trustworthy across both chat modes.

**Current Phase:** Milestone 4 - LLM request and stream lifecycle

---

## Milestone 4: LLM request and stream lifecycle

### 4.1 Non-streaming chat lifecycle

- [ ] **Test**: `test_chat_logs_request_lifecycle_and_completion_metadata()`
  - Extend `tests/test_llm_observability.py`
  - Fake a successful `chat()` response with usage counts
  - Assert logs include `llm.request.start` and `llm.request.completed`
  - Verify `operation=chat`, `messages=`, `response_chars=`, `prompt_tokens=`, `completion_tokens=`, and `duration_ms=`
- [ ] **Implement**: align `KimiProvider.chat()` request lifecycle metadata if the test exposes a gap
  - Keep the logs metadata-first
  - Avoid logging full prompts or full responses
- [ ] **Run**: `uv run pytest tests/test_llm_observability.py::test_chat_logs_request_lifecycle_and_completion_metadata -v`

### 4.2 Tool-aware non-streaming lifecycle

- [ ] **Test**: `test_chat_with_tools_logs_request_lifecycle_and_tool_counts()`
  - Extend `tests/test_llm_observability.py`
  - Fake a successful `chat_with_tools()` response with a tool call and usage counts
  - Assert logs include `llm.request.start` and `llm.request.completed`
  - Verify `operation=chat_with_tools`, `messages=`, `tools=`, `tool_calls=`, `response_chars=`, `prompt_tokens=`, `completion_tokens=`, and `duration_ms=`
- [ ] **Implement**: keep `KimiProvider.chat_with_tools()` aligned with the shared request event format
  - Ensure tool counts remain explicit
  - Preserve the same surface vocabulary as `chat()`
- [ ] **Run**: `uv run pytest tests/test_llm_observability.py::test_chat_with_tools_logs_request_lifecycle_and_tool_counts -v`

### 4.3 Streaming retry exhaustion

- [ ] **Test**: `test_stream_chat_logs_failed_request_after_retries_are_exhausted()`
  - Extend `tests/test_llm_observability.py`
  - Force `_create_stream` to fail on every attempt
  - Assert logs include `llm.request.retry` and `llm.request.failed`
  - Verify `operation=stream_chat`, `attempts=`, `error_type=`, `error=`, and `duration_ms=`
- [ ] **Implement**: keep `_retry_async()` / `stream_chat()` failure logging aligned with the shared LLM surface contract
  - Preserve the original exception mapping
  - Keep retry metadata concise and consistent
- [ ] **Run**: `uv run pytest tests/test_llm_observability.py::test_stream_chat_logs_failed_request_after_retries_are_exhausted -v`

### 4.4 Tool-aware streaming retry exhaustion

- [ ] **Test**: `test_stream_chat_with_tools_logs_failed_request_after_retries_are_exhausted()`
  - Extend `tests/test_llm_observability.py`
  - Force `stream_chat_with_tools()` to fail on every attempt
  - Assert logs include `llm.request.retry` and `llm.request.failed`
  - Verify `operation=stream_chat_with_tools`, `attempts=`, `tools=`, `error_type=`, `error=`, and `duration_ms=`
- [ ] **Implement**: keep `_create_stream_with_retry()` / `stream_chat_with_tools()` failure logging consistent with `stream_chat()`
  - Make sure the tool-aware path reports the same failure metadata shape
- [ ] **Run**: `uv run pytest tests/test_llm_observability.py::test_stream_chat_with_tools_logs_failed_request_after_retries_are_exhausted -v`

---

## Files to Modify

1. `tests/test_llm_observability.py` - new regression coverage for non-streaming and failure cases
2. `src/alfred/llm.py` - align request lifecycle metadata if any test exposes a gap

## Verification Commands

```bash
uv run pytest tests/test_llm_observability.py -q
uv run ruff check src/ tests/
uv run mypy --strict src/
uv run pytest -m "not slow"
```

## Commit Strategy

Suggested atomic commits:
- `test(llm): cover chat request lifecycle logging`
- `test(llm): cover chat-with-tools lifecycle logging`
- `test(llm): cover stream retry failure logging`
- `test(llm): cover stream-with-tools retry failure logging`
- `fix(llm): align request lifecycle metadata`

## Next Task

- [ ] **Test**: `test_chat_logs_request_lifecycle_and_completion_metadata()`
- [ ] **Implement**: align `KimiProvider.chat()` request lifecycle metadata if needed
- [ ] **Run**: `uv run pytest tests/test_llm_observability.py::test_chat_logs_request_lifecycle_and_completion_metadata -v`
