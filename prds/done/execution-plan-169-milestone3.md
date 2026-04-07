# Execution Plan: PRD #169 - Milestone 3 Inspection Surfaces

## Overview
Expose one hybrid inspection surface that shows current help state and learned state from the same durable support-memory source of truth.

## Current Repo Constraints
- Runtime support truth already resolves through `src/alfred/support_policy.py`; inspection must reuse that seam.
- `src/alfred/interfaces/webui/server.py` already supports slash-command responses through the websocket command channel.
- `src/alfred/support_reflection.py` now owns the reflection read models and should stay the single inspection contract surface.

## Success Signal
- Alfred can show effective support values, effective relational values, active runtime patterns, candidate/confirmed patterns, and recent change history through one bounded inspection request.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/alfred/support_reflection.py src/alfred/storage/sqlite.py src/alfred/alfred.py src/alfred/interfaces/webui/server.py src/alfred/interfaces/webui/contracts.py tests/test_support_reflection.py tests/webui/test_reflection_commands.py tests/webui/fakes.py`
- **Typing:** `uv run mypy --strict src/alfred/support_reflection.py src/alfred/storage/sqlite.py src/alfred/alfred.py src/alfred/interfaces/webui/server.py src/alfred/interfaces/webui/contracts.py`
- **Targeted tests:** `uv run pytest --no-cov -p no:cacheprovider tests/test_support_reflection.py tests/webui/test_reflection_commands.py -q`

---

## Phase 1: Snapshot and drill-down contracts

- [x] Test: `test_support_inspection_snapshot_reads_runtime_and_learned_state_from_one_source_of_truth()` - verify one inspection snapshot combines effective values, active patterns, candidate/confirmed patterns, and recent changes.
- [x] Implement: add the hybrid snapshot and drill-down contracts in `src/alfred/support_reflection.py`.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_inspection_snapshot_reads_runtime_and_learned_state_from_one_source_of_truth -v`

- [x] Test: `test_support_inspection_drilldowns_explain_pattern_update_event_and_effective_value_details()` - verify callers can inspect a pattern, an update event, and one effective-value explanation.
- [x] Implement: add the drill-down helpers and bounded text renderers.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_inspection_drilldowns_explain_pattern_update_event_and_effective_value_details -v`

## Phase 2: Storage and command surface

- [x] Test: `test_support_reflection_storage_lists_patterns_for_inspection_and_recent_update_events()` - verify SQLite lists the inspection inputs in deterministic order.
- [x] Implement: add inspection list queries in `src/alfred/storage/sqlite.py`.
- [x] Run: `uv run pytest tests/storage/test_support_reflection_storage.py::test_support_reflection_storage_lists_patterns_for_inspection_and_recent_update_events -v`

- [x] Test: `test_support_command_renders_snapshot_through_chat_message_flow()` - verify `/support` returns the inspection surface through the existing assistant-message websocket path.
- [x] Implement: add Alfred wrapper methods plus the `/support` Web UI command handler.
- [x] Run: `uv run pytest tests/webui/test_reflection_commands.py::test_support_command_renders_snapshot_through_chat_message_flow -v`
