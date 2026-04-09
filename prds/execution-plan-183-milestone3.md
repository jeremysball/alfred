# Execution Plan: PRD #183 - Milestone 3A: Deterministic operational outcome observations

## Overview
Start Milestone 3 with the narrowest durable observation lane: deterministic `OutcomeObservation(source_type="work_state_transition")` rows derived from structured work-state writes. This slice links task, blocker, open-loop, and arc transitions to the latest matching `SupportAttempt` for the same active arc, while deferring next-user-turn and semantic observation extraction to later PRDs.

## Current Repo Constraints
- `src/alfred/storage/sqlite.py` already persists the v2 support-learning bundle (`SupportAttempt`, `OutcomeObservation`, `LearningCase`) but no runtime path currently appends operational observations automatically.
- Operational work-state writes already flow through public SQLite seams: `save_operational_arc()`, `save_arc_task()`, `save_arc_blocker()`, and `save_arc_open_loop()`.
- `SupportAttempt` already stores `active_arc_id`, which gives this milestone one deterministic linking seam from an operational transition back to the latest relevant attempt.
- There is no existing query helper or index for loading the latest attempt by `active_arc_id`, so this slice must add one without broadening into full case finalization yet.
- Milestone 2 now writes real attempt refs from `chat_stream()`, so Milestone 3A can build on those durable attempts instead of inventing placeholders.
- Option A deliberately defers conversational / semantic observation extraction so this milestone stays inside PRD #183 and avoids pulling sibling PRDs #184 and #189 forward.

## Success Signal
- When a task, blocker, open loop, or operational arc changes state after a reply, the store appends one `OutcomeObservation` with `source_type="work_state_transition"` and links it to the latest `SupportAttempt` whose `active_arc_id` matches that arc.
- The saved observation records deterministic operational signals such as `task_started`, `blocker_resolved`, `open_loop_closed`, `arc_resumed`, or other explicitly mapped status transitions.
- Re-saving unchanged state or writing state for an arc with no matching attempt does not fabricate or append observations.
- Existing operational storage behavior still works when no support attempt is present.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/storage/test_support_learning_storage.py` and `uv run mypy --strict src/`
- **Targeted tests:** run the smallest pytest command listed under each task

---

## Phase 1: Link operational transitions to the latest matching attempt

### Persist deterministic work-state observations from public storage seams

- [x] Test: add `test_sqlite_store_records_work_state_transition_observations_for_latest_matching_arc_attempt()` in `tests/storage/test_support_learning_storage.py` — verify task, blocker, open-loop, and arc transitions append ordered `work_state_transition` observations on the latest matching attempt for that arc.
- [x] Implement: extend `src/alfred/storage/sqlite.py` with the minimal latest-attempt lookup, deterministic transition mapping, and observation persistence needed for `save_operational_arc()`, `save_arc_task()`, `save_arc_blocker()`, and `save_arc_open_loop()`.
- [x] Run: `uv run pytest tests/storage/test_support_learning_storage.py::test_sqlite_store_records_work_state_transition_observations_for_latest_matching_arc_attempt -v`

### Skip non-matching or non-transition writes cleanly

- [x] Test: add `test_sqlite_store_skips_work_state_transition_observations_without_matching_arc_attempt_or_status_change()` in `tests/storage/test_support_learning_storage.py` — verify unmatched arcs and unchanged status upserts do not append observations.
- [x] Implement: keep the new work-state observation path bounded so only explicitly mapped transitions on the matching arc produce new rows.
- [x] Run: `uv run pytest tests/storage/test_support_learning_storage.py::test_sqlite_store_skips_work_state_transition_observations_without_matching_arc_attempt_or_status_change -v`

---

## Final phase verification

- [x] Run: `uv run ruff check src/ tests/storage/test_support_learning_storage.py`
- [x] Run: `uv run mypy --strict src/`
- [x] Run: `uv run pytest tests/storage/test_support_learning_storage.py -v`

## Files to Modify

1. `prds/execution-plan-183-milestone3.md` - milestone plan and validation record
2. `src/alfred/storage/sqlite.py` - latest-attempt lookup plus operational observation persistence from public work-state seams
3. `tests/storage/test_support_learning_storage.py` - public storage-seam regression tests for deterministic work-state observations

## Commit Strategy

Keep this slice atomic:
- `feat(storage): persist v2 work-state outcome observations`
