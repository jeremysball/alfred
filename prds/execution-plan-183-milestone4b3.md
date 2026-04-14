# Execution Plan: PRD #183 - Milestone 4B.3: Apply v2 case-learning from operational observations

## Overview
Now that bounded adaptation (`LearningSituation`) is retired (4B.2) and runtime value resolution prefers v2 ledger entries (4B.1), we need a deterministic **runner** that turns the operational observation lane (3A) into finalized cases (4A) and value-ledger updates (5A).

This phase is **operational-only**: it reacts to `work_state_transition` observations written via the existing public SQLite work-state seams.

## Current Repo Constraints
- Work-state writes (`save_operational_arc`, `save_arc_task`, `save_arc_blocker`, `save_arc_open_loop`) open an `aiosqlite` connection and commit at the end.
- `_maybe_save_work_state_transition_observation(...)` currently inserts an `OutcomeObservation` inside that same connection, but does **not** finalize a `LearningCase` or apply case-based ledger learning.
- Public helpers `finalize_support_learning_case(attempt_id)` and `apply_support_case_learning(case_id)` currently open their **own** SQLite connections and commit. Calling them from inside a work-state write would cross transaction boundaries and risks seeing partial state.
- Case-based ledger promotion requires `LearningCase.status == "complete"` and `promotion_eligibility == True`. With a single strong positive operational signal (e.g. `task_completed`), a case should become promotable, but the derived ledger entry should still be `shadow` until the per-scope threshold is met.
- Conversational/semantic extraction is explicitly out of scope for PRD #183 (owned by PRD #189).

## Success Signal (observable)
When a work-state write produces a `work_state_transition` observation for a matching `SupportAttempt`:
1. A `LearningCase` is finalized/upserted for that attempt (`case-{attempt_id}`).
2. Case-based learning is applied for that case, persisting:
   - at least one v2 `support_value_ledger_entries` row (typically `status="shadow"` on first evidence)
   - at least one v2 `support_ledger_update_events` row describing the new/changed status.

And when the work-state write produces **no** observation (no transition signal or no matching attempt), no case/ledger writes occur.

## Validation Workflow
**Python**

- Static checks:
  ```bash
  uv run ruff check src/ tests/storage/test_support_learning_storage.py
  uv run mypy --strict src/
  ```
- Targeted tests:
  ```bash
  uv run pytest tests/storage/test_support_learning_storage.py -v
  ```

---

## Phase 1: End-to-end storage contract from work-state transition → ledger rows

### SQLite work-state seam

- [x] Test: `test_sqlite_store_work_state_transition_finalizes_case_and_applies_v2_value_ledger_updates()` in `tests/storage/test_support_learning_storage.py`
  - Arrange: persisted `SupportAttempt` for an arc + persisted operational arc/task
  - Act: perform a status change that yields a known positive signal (e.g. task `todo` → `done`)
  - Assert:
    - one `OutcomeObservation(source_type="work_state_transition")` exists for the attempt
    - `get_support_learning_case("case-{attempt_id}")` exists and is `promotion_eligibility == True`
    - `list_support_value_ledger_entries()` contains a derived entry with:
      - `source == "auto_case"`
      - `status == "shadow"` (first promotable case)
      - `scope.type == "arc"` and `scope.id == attempt.active_arc_id`
    - `list_support_ledger_update_events()` contains a new event with `new_status == "shadow"` and `trigger_case_ids` containing the case id

- [x] Implement: run case finalization + case-learning inside `_maybe_save_work_state_transition_observation(...)` using the *existing* `db` connection
  - Add internal transactional helpers:
    - `_finalize_support_learning_case_in_tx(db, attempt_id) -> LearningCase | None`
    - `_apply_support_case_learning_in_tx(db, case_id) -> SupportLedgerDerivationResult | None`
  - Refactor the public methods:
    - `finalize_support_learning_case(attempt_id)` should open a connection and delegate to `_finalize_support_learning_case_in_tx(...)` then commit.
    - `apply_support_case_learning(case_id)` should open a connection and delegate to `_apply_support_case_learning_in_tx(...)` then commit.
  - In `_maybe_save_work_state_transition_observation(...)`, after inserting the observation:
    - finalize the case for `attempt.attempt_id`
    - if the case is promotable, apply case learning for `case.case_id`
    - do **not** commit inside this helper; rely on the surrounding work-state save method’s commit.

- [x] Run: `uv run pytest tests/storage/test_support_learning_storage.py::test_sqlite_store_work_state_transition_finalizes_case_and_applies_v2_value_ledger_updates -v`

---

## Phase 2: Negative-path guard (no transition/no attempt)

- [x] Test: `test_sqlite_store_work_state_transition_does_not_apply_case_learning_when_no_observation_is_written()` in `tests/storage/test_support_learning_storage.py`
  - Arrange: persisted arc/task but either:
    - no matching attempt for the arc, or
    - status update that does not produce a transition signal
  - Assert: `list_support_value_ledger_entries()` and `list_support_ledger_update_events()` remain empty and no `support_learning_cases` row is created.

- [x] Implement: ensure `_maybe_save_work_state_transition_observation(...)` only triggers finalize/apply when an observation was actually upserted (and an attempt exists).

- [x] Run: `uv run pytest tests/storage/test_support_learning_storage.py::test_sqlite_store_work_state_transition_does_not_apply_case_learning_when_no_observation_is_written -v`

---

## Final phase verification

- [x] Run: `uv run ruff check src/ tests/storage/test_support_learning_storage.py`
- [x] Run: `uv run mypy --strict src/`
- [x] Run: `uv run pytest tests/storage/test_support_learning_storage.py -v`

## Files to Modify
1. `src/alfred/storage/sqlite.py` - apply finalize+case-learning during operational observation writes; add transactional helpers
2. `tests/storage/test_support_learning_storage.py` - end-to-end contract tests for work-state-driven case+ledger updates

## Commit Strategy
Two atomic commits:
1. `test(prd-183): prove work-state transitions finalize cases and write v2 ledger rows`
2. `feat(prd-183): apply case learning during work-state observation writes`
