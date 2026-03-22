# Execution Plan: PRD #144 - Core Observability and Differentiated Logging Surfaces

## Overview

Add a shared logging-surface contract, then wire Alfred's core, Web UI, and browser client logs through it so operators can instantly tell where a line came from and how to follow a turn end-to-end.

**Current state:** root vs Web UI logging scoping already has regression coverage; the remaining work is the shared formatter, richer lifecycle instrumentation, browser-client prefixes, and docs/verification polish.

---

## Milestone 1: Define the surface model and logging contract

### Component: Shared observability module

- [ ] **Test**: `test_surface_names_are_stable()`
  - Create `tests/test_observability.py`
  - Assert the surface taxonomy includes `core`, `webui-server`, `webui-client`, `llm`, `tools`, and `storage`
- [ ] **Test**: `test_surface_formatter_colors_prefix_in_tty()`
  - Assert a TTY console stream gets a colorized `[surface]` prefix
- [ ] **Test**: `test_surface_formatter_emits_plain_prefix_when_not_tty()`
  - Assert a non-TTY stream gets a plain `[surface]` prefix with no ANSI escapes
- [ ] **Test**: `test_surface_formatter_routes_webui_server_records_to_webui_server_surface()`
  - Assert logger names from the Web UI server map to the Web UI server surface automatically
- [ ] **Implement**: add `src/alfred/observability.py`
  - Centralize surface taxonomy, prefix rendering, and shared logging helpers
- [ ] **Run**: `uv run pytest tests/test_observability.py -v`

### Component: Logging setup contract

- [ ] **Test**: `test_configure_logging_emits_file_records_with_surface_fields()`
  - Verify file output includes explicit `surface=...` metadata and stays ANSI-free
- [ ] **Test**: `test_configure_logging_allows_webui_debug_without_enabling_core_debug()`
  - Verify Web UI debug logs can pass through independently of root/core verbosity
- [ ] **Implement**: wire `configure_logging()` into the CLI logging bootstrap
  - Keep file logs grep-friendly and console logs readable
- [ ] **Run**: `uv run pytest tests/test_observability.py -v`

---

## Milestone 2: Separate core and Web UI logging controls cleanly

### Component: CLI wiring

- [x] **Test**: `test_root_log_debug_does_not_enable_webui_debug()`
- [x] **Test**: `test_webui_log_debug_enables_webui_debug_without_root_debug()`
- [x] **Test**: `test_root_and_webui_log_debug_can_be_enabled_together()`
- [ ] **Implement**: keep the CLI callback wiring aligned with separate root and Web UI log scopes
  - Root `--log` controls Alfred/core verbosity
  - `webui --log` controls Web UI debug instrumentation
- [ ] **Run**: `uv run pytest tests/test_cli_webui_logging.py -v`

---

## Milestone 3: Instrument core turn and context lifecycle

### Component: Alfred turn lifecycle

- [ ] **Test**: `test_chat_stream_logs_turn_start_context_and_completion()`
  - Add or extend a focused behavioral test around `Alfred.chat_stream()`
  - Capture logs and assert turn start, context assembly, and turn completion events are present
- [ ] **Implement**: add turn lifecycle logging in `src/alfred/alfred.py`
  - Log start/end/failure/cancellation with duration metadata
- [ ] **Run**: `uv run pytest tests/test_alfred_turn_logging.py -v`

### Component: Context assembly lifecycle

- [ ] **Test**: `test_context_builder_logs_memory_search_counts_and_budget_decisions()`
  - Assert the context builder logs selected counts, similarity filtering, and truncation decisions
- [ ] **Implement**: add structured context logs in `src/alfred/context.py`
- [ ] **Run**: `uv run pytest tests/test_context_memory_scoring.py -v`

---

## Milestone 4: Instrument LLM request and stream lifecycle

### Component: LLM lifecycle

- [ ] **Test**: `test_llm_stream_logs_request_start_and_completion_metadata()`
  - Assert request start, first-token, completion, and failure paths are logged
- [ ] **Implement**: enrich `src/alfred/llm.py` with structured request/stream logging
- [ ] **Run**: `uv run pytest tests/test_llm.py -v`

---

## Milestone 5: Instrument tool and storage surfaces

### Component: Tool lifecycle

- [ ] **Test**: `test_agent_logs_tool_start_output_and_end_events()`
  - Assert tool execution emits lifecycle logs with duration/output metadata
- [ ] **Implement**: add tool lifecycle logs in `src/alfred/agent.py`
- [ ] **Run**: `uv run pytest tests/test_agent_run_stream.py -v`

### Component: Storage lifecycle

- [ ] **Test**: `test_sqlite_store_logs_search_and_persistence_boundaries()`
  - Assert storage writes/searches emit useful debug lines for slow/failing paths
- [ ] **Implement**: add structured storage logs in `src/alfred/storage/sqlite.py` and session persistence edges
- [ ] **Run**: `uv run pytest tests/storage/test_sqlite_vec.py -v`

---

## Milestone 6: Align Web UI server/client logs with the same surface model

### Component: Web UI server surface

- [ ] **Test**: `test_webui_server_logs_use_the_webui_server_surface()`
  - Assert the FastAPI server emits surface-tagged debug lines
- [ ] **Implement**: update `src/alfred/interfaces/webui/server.py` to emit structured surface-tagged logs
- [ ] **Run**: `uv run pytest tests/webui/test_server.py -v`

### Component: Web UI client surface

- [ ] **Test**: `test_webui_client_console_logs_are_prefixed_with_surface()`
  - Add/extend static-source checks for `websocket-client.js`, `main.js`, and related browser-side helpers
- [ ] **Implement**: prefix browser console logs with `[webui-client]`
  - Keep browser debug output distinct from server logs
- [ ] **Run**: `uv run pytest tests/webui/test_frontend_logging.py -v`

---

## Milestone 7: Documentation and final verification

### Component: Docs and README

- [ ] **Test**: `test_readme_documents_surface_scoped_logging()`
  - Assert the README explains root vs Web UI scopes and the new prefix behavior
- [ ] **Implement**: update `README.md` and any concise debugging docs
- [ ] **Run**: `uv run pytest tests/test_cli_webui_logging.py tests/webui/test_frontend_logging.py -v`

### Component: Final sweep

- [ ] **Run**: `uv run ruff check src/ tests/`
- [ ] **Run**: `uv run mypy --strict src/`
- [ ] **Run**: `uv run pytest`
- [ ] **Run**: `uv run alfred webui --port 8080`

---

## Files to Modify

1. `src/alfred/observability.py` - shared surface taxonomy, formatter, and logging helpers
2. `src/alfred/cli/main.py` - logging bootstrap wiring
3. `src/alfred/alfred.py` - turn lifecycle logging
4. `src/alfred/context.py` - context and retrieval logging
5. `src/alfred/llm.py` - LLM request/stream logging
6. `src/alfred/agent.py` - tool lifecycle logging
7. `src/alfred/storage/sqlite.py` - storage lifecycle logging
8. `src/alfred/interfaces/webui/server.py` - Web UI server surface logs
9. `src/alfred/interfaces/webui/static/js/websocket-client.js` - browser client surface prefixes
10. `src/alfred/interfaces/webui/static/js/main.js` - browser client surface prefixes
11. `src/alfred/interfaces/webui/static/js/scrapbook.js` - browser client surface prefixes
12. `src/alfred/interfaces/webui/static/js/audio-manager.js` - browser client surface prefixes
13. `tests/test_observability.py` - new formatter and surface contract tests
14. `tests/test_cli_webui_logging.py` - existing root/Web UI scoping regression tests
15. `tests/webui/test_frontend_logging.py` - browser client logging surface checks

## Commit Strategy

Suggested atomic commits:
- `test(observability): codify surface formatting contract`
- `feat(observability): add shared surface-aware logging helpers`
- `fix(cli): route logs through surface-aware handlers`
- `test(core): cover turn and context lifecycle logging`
- `fix(core): add turn, llm, tool, and storage observability`
- `fix(webui): prefix browser logs with webui-client surface`
- `docs(readme): document surface-scoped logging`
