# Execution Plan: PRD #169 - Milestone 4 Correction Flows

## Overview
Add typed correction flows that confirm or reject patterns and correct, reset, or scope-limit learned profile values without allowing direct pattern-text editing.

## Current Repo Constraints
- `SupportPattern` already stores the durable candidate/confirmed/rejected state.
- `SupportProfileValue` and `SupportProfileUpdateEvent` already form the auditable behavior layer for durable help changes.
- Correction flows must mutate those durable objects directly rather than inventing a parallel correction record.

## Success Signal
- Alfred can apply typed correction actions, persist the resulting durable pattern/value changes, and return a clear user-facing confirmation.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/alfred/support_reflection.py src/alfred/storage/sqlite.py src/alfred/alfred.py src/alfred/interfaces/webui/server.py src/alfred/interfaces/webui/contracts.py tests/test_support_reflection.py tests/webui/test_reflection_commands.py tests/webui/fakes.py`
- **Typing:** `uv run mypy --strict src/alfred/support_reflection.py src/alfred/storage/sqlite.py src/alfred/alfred.py src/alfred/interfaces/webui/server.py src/alfred/interfaces/webui/contracts.py`
- **Targeted tests:** `uv run pytest --no-cov -p no:cacheprovider tests/test_support_reflection.py tests/webui/test_reflection_commands.py -q`

---

## Phase 1: Typed correction actions

- [x] Test: `test_support_correction_actions_allow_pattern_confirmation_and_profile_value_edits_only()` - verify the v1 action surface allows the intended corrections and makes direct pattern-text editing impossible.
- [x] Implement: add the typed correction action contracts in `src/alfred/support_reflection.py`.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_correction_actions_allow_pattern_confirmation_and_profile_value_edits_only -v`

- [x] Test: `test_support_correction_actions_capture_auditable_targets_and_requested_scope_changes()` - verify the action contracts preserve target identity and requested scope changes.
- [x] Implement: add validation for auditable action payloads.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_correction_actions_capture_auditable_targets_and_requested_scope_changes -v`

## Phase 2: Durable mutation flow

- [x] Test: `test_support_reflection_runtime_applies_pattern_confirmation_and_profile_value_corrections_traceably()` - verify confirm/reject and direct value corrections update durable truth and log the change.
- [x] Implement: add correction application logic in `src/alfred/support_reflection.py`.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_reflection_runtime_applies_pattern_confirmation_and_profile_value_corrections_traceably -v`

- [x] Test: `test_support_reflection_runtime_scope_limit_and_reset_rewrite_profile_value_scope_cleanly()` - verify scope-limit and reset flows move or remove the durable override cleanly.
- [x] Implement: add scoped delete/write behavior plus update-event logging.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_reflection_runtime_scope_limit_and_reset_rewrite_profile_value_scope_cleanly -v`

## Phase 3: Command surface

- [x] Test: `test_support_confirm_command_routes_typed_correction_action()` - verify the Web UI command path builds and applies a typed correction action instead of a generic blob.
- [x] Implement: add the correction subcommands under `/support`.
- [x] Run: `uv run pytest tests/webui/test_reflection_commands.py::test_support_confirm_command_routes_typed_correction_action -v`
