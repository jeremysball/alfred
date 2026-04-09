# Execution Plan: PRD #183 - Milestone 1: V2 learning schema and storage contract

## Overview
Land the case-based v2 support-learning storage contract without yet claiming the live runtime is fully case-based. This phase defines the typed attempt / observation / case artifacts, introduces the v2 value-pattern ledger statuses and provenance fields, and adds a support-learning-only SQLite cutover that can discard old v1 learning rows while preserving sessions and support-memory state.

## Current Repo Constraints
- `src/alfred/memory/support_learning.py` is centered on `LearningSituation`, `SupportPattern`, and `SupportProfileUpdateEvent`, and current tests assert those v1 record helpers and bounded-adaptation outputs directly.
- `src/alfred/support_policy.py` still creates and persists a `LearningSituation` during reply-time through `_maybe_apply_bounded_adaptation()`. Milestone 1 should not pretend the runtime is already case-based before reply-time capture, observation capture, and case finalization ship.
- `src/alfred/storage/sqlite.py` creates support-memory and support-learning tables inside the same support-memory bootstrap path. The v2 cutover must not damage sessions, operational arcs, blockers, tasks, open loops, episodes, or existing curated memory tables.
- `src/alfred/memory/support_profile.py` defines the currently loaded runtime value type with v1 statuses (`observed`, `candidate`, `confirmed`). Milestone 1 must either stage the richer v2 ledger types carefully or update callers deliberately so `/context` and runtime loading do not claim unshipped statuses.
- Existing local databases may already contain v1 support-learning tables and rows. The user explicitly approved a clean replacement with no v1 backfill, so this phase should prefer a support-learning-only destructive cutover over compatibility glue.
- `/context` and `/support` currently expose the v1 learned-state story. This milestone should land the storage contract those later surfaces will read, but should not partially expose a v2 ledger before the inspection work is implemented.

## Success Signal
- Fresh and existing SQLite stores initialize with the v2 support-learning schema while leaving sessions and support-memory tables intact.
- The store can round-trip `SupportAttempt`, `OutcomeObservation`, `LearningCase`, v2 value-ledger rows, v2 pattern rows, and update events through explicit typed save/load/list helpers.
- Attempt persistence rejects or skips writes when real session or message references are missing; no v2 row is ever stored with fabricated placeholders such as `session_id="runtime"`.
- This phase proves the storage boundary and cutover behavior directly, while leaving the live runtime migration for later PRD #183 milestones.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/test_support_learning.py tests/storage/test_support_learning_storage.py` and `uv run mypy --strict src/`
- **Targeted tests:** run the smallest pytest command listed under each task

---

## Phase 1: Typed v2 learning artifacts

### Attempt / observation / case record contract

- [ ] Test: `test_v2_learning_artifacts_round_trip_with_real_refs()` in `tests/test_support_learning.py` — verify `SupportAttempt`, `OutcomeObservation`, and `LearningCase` preserve real session/message refs, signals, scoring fields, scope, and status semantics through record helpers.
- [ ] Implement: replace the v1-only learning artifact definitions in `src/alfred/memory/support_learning.py` with the minimal v2 typed models and validators needed for attempt / observation / case persistence, while keeping untouched callers compiling until later runtime phases cut over.
- [ ] Run: `uv run pytest tests/test_support_learning.py::test_v2_learning_artifacts_round_trip_with_real_refs -v`

### Value / pattern ledger status contract

- [ ] Test: `test_v2_value_pattern_and_update_event_records_preserve_status_and_provenance()` in `tests/test_support_learning.py` — verify v2 value rows, pattern rows, and update events preserve explicit statuses, evidence counts, contradiction counts, source refs, and `why` metadata through record helpers.
- [ ] Implement: add the minimal v2 ledger models and status validators in `src/alfred/memory/support_learning.py` and, where unavoidable, stage or extend `src/alfred/memory/support_profile.py` so the richer ledger can coexist with the still-v1 runtime loading surface until later milestones replace it.
- [ ] Run: `uv run pytest tests/test_support_learning.py::test_v2_value_pattern_and_update_event_records_preserve_status_and_provenance -v`

---

## Phase 2: SQLite v2 storage boundary

### Case bundle round trip through the store

- [ ] Test: `test_sqlite_store_round_trips_v2_learning_case_bundle()` in `tests/storage/test_support_learning_storage.py` — verify the store can save and read one attempt with linked observations, one finalized case, related value/pattern ledger rows, and update events without losing ordering, refs, or scoring fields.
- [ ] Implement: add the new v2 support-learning tables and typed save/load/list helpers in `src/alfred/storage/sqlite.py`, and wire them to the v2 record helpers in `src/alfred/memory/support_learning.py`.
- [ ] Run: `uv run pytest tests/storage/test_support_learning_storage.py::test_sqlite_store_round_trips_v2_learning_case_bundle -v`

### Real-reference persistence invariants

- [ ] Test: `test_sqlite_store_rejects_support_attempt_without_real_session_and_message_refs()` in `tests/storage/test_support_learning_storage.py` — verify the store refuses fabricated session/message placeholders and leaves the v2 learning tables unchanged when refs are missing.
- [ ] Implement: enforce the persistence invariants in `src/alfred/storage/sqlite.py` and the v2 model validators so missing required refs fail fast or cleanly skip persistence instead of inventing stand-ins.
- [ ] Run: `uv run pytest tests/storage/test_support_learning_storage.py::test_sqlite_store_rejects_support_attempt_without_real_session_and_message_refs -v`

---

## Phase 3: Support-learning-only cutover from v1

### Destructive v1-to-v2 learning schema reset

- [ ] Test: `test_store_init_replaces_v1_learning_schema_without_touching_support_memory()` in `tests/storage/test_support_learning_storage.py` — verify store initialization against a database with the old learning tables drops and recreates only the support-learning-specific schema, preserves sessions and support-memory rows, and leaves the store ready for v2 writes.
- [ ] Implement: add a support-learning schema-version or table-shape check in `src/alfred/storage/sqlite.py` that performs a support-learning-only destructive reset for the obsolete v1 learning tables and vec indexes, without backfilling old rows.
- [ ] Run: `uv run pytest tests/storage/test_support_learning_storage.py::test_store_init_replaces_v1_learning_schema_without_touching_support_memory -v`

### Final phase verification

- [ ] Run: `uv run ruff check src/ tests/test_support_learning.py tests/storage/test_support_learning_storage.py`
- [ ] Run: `uv run mypy --strict src/`
- [ ] Run: `uv run pytest tests/test_support_learning.py tests/storage/test_support_learning_storage.py -v`

---

## Files to Modify

1. `src/alfred/memory/support_learning.py` - replace v1-only learning artifacts with v2 attempt / observation / case and ledger models
2. `src/alfred/memory/support_profile.py` - stage any necessary status or value-contract changes that the v2 ledger requires without lying about runtime loading
3. `src/alfred/storage/sqlite.py` - add v2 learning tables, real-ref invariants, load/save helpers, and support-learning-only cutover logic
4. `tests/test_support_learning.py` - new v2 record-helper and status-contract tests
5. `tests/storage/test_support_learning_storage.py` - new SQLite round-trip, invariant, and cutover tests
6. `prds/183-support-learning-v2-case-based-adaptation-and-full-inspection.md` - only if milestone wording or decisions need to be clarified while the storage contract lands

## Commit Strategy

Each completed test → implement → run block should map to one atomic commit:
- `refactor(memory): define v2 support-learning artifacts`
- `refactor(storage): persist v2 support-learning case bundles`
- `fix(storage): reject support-learning writes without real refs`
- `refactor(storage): cut over support-learning schema to v2`
