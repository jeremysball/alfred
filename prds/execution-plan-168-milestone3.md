# Execution Plan: PRD #168 - Milestone 3: Add Episode-Level Intervention Logging

> **Prerequisite satisfied on this branch:** `prds/execution-plan-167-addendum-transcript-normalization.md`.
>
> Milestone 3 now assumes canonical `session_messages` storage and message-ID-based `EvidenceRef` spans from the PRD #167 transcript-normalization addendum.

## Overview
This phase adds durable intervention records linked to support episodes after transcript provenance has been normalized. The goal is to capture what Alfred tried, which relational and support values were applied, what signals followed, and which first-class evidence refs support the record, then expose minimal query surfaces by episode, arc, context, and applied dimension. It stops short of behavior compilation and bounded adaptation.

## Current Repo Constraints
- `src/alfred/memory/support_memory.py` already defines `SupportEpisode`, which stores summary fields such as `interventions_attempted`, `response_signals`, and `outcome_signals`. Milestone 3 should add intervention-level detail without breaking the existing episode summary contract or its storage tests.
- `src/alfred/storage/sqlite.py` is the single persistence boundary and already owns the support-memory schema for episodes, evidence refs, and support-profile values. Intervention logging should fit beside those tables instead of introducing another storage path.
- Applied relational and support values must reuse the fixed registries in `src/alfred/memory/support_profile.py`. Intervention logs should not accept arbitrary dimension/value pairs.
- Intervention evidence should reuse first-class message-ID-based support-memory provenance from the PRD #167 transcript-normalization addendum rather than storing untyped string IDs.
- Existing support-memory models use explicit `to_record()` / `from_record()` helpers and JSON-serialized list fields. Milestone 3 should match that style instead of inventing a new persistence convention.
- This phase should stop at durable logging and retrieval. It should not compile runtime behavior contracts, infer contexts, or auto-update support-profile values.

## Success Signal
- Alfred can create typed intervention records linked to support episodes with validated context, optional `arc_id`, applied relational/support values, `behavior_contract_summary`, response signals, outcome signals, typed evidence refs, and timestamps.
- SQLite round-trips intervention records without losing applied values, signal ordering, or evidence provenance.
- Alfred can query logged interventions by episode, arc, context, and applied dimension, giving later milestones durable evidence for policy resolution and adaptation.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/test_support_intervention.py tests/storage/test_support_intervention_storage.py` and `uv run mypy --strict src/`
- **Targeted tests for this phase:** `uv run pytest tests/test_support_intervention.py tests/storage/test_support_intervention_storage.py -v`

---

## Phase 1: Milestone 3 - Add episode-level intervention logging

### Typed intervention contract

- [x] Test: `test_support_intervention_validates_context_applied_values_and_evidence_refs()` - verify typed intervention records accept valid context-scoped support/relational summaries plus first-class evidence refs and reject unknown dimensions, invalid values, malformed signal entries, or malformed provenance refs.
- [x] Implement: add a typed `SupportIntervention` model plus lightweight same-session `SupportInterventionMessageRef` spans that validate context IDs against the v1 taxonomy, applied values against the support-profile registries, and intervention provenance against the normalized transcript message-ID contract.
- [x] Run: `uv run pytest tests/test_support_intervention.py::test_support_intervention_validates_context_applied_values_and_evidence_refs -v`

### Persisted intervention record round-trip

- [x] Test: `test_support_intervention_round_trips_through_storage_records()` - verify intervention records serialize and deserialize with applied values, signals, evidence refs, and timestamps intact.
- [x] Implement: add `to_record()` / `from_record()` support for intervention logs using the existing support-memory persistence style with JSON-serialized maps, signal lists, and message-span refs.
- [x] Run: `uv run pytest tests/test_support_intervention.py::test_support_intervention_round_trips_through_storage_records -v`

### SQLite support intervention storage

- [ ] Test: `test_support_interventions_round_trip_through_sqlite_store()` - verify saving and loading multiple interventions preserves episode linkage, applied values, and evidence provenance ordering.
- [ ] Implement: add the intervention table(s), indexes, and `SQLiteStore` save/get/list-by-episode helpers for intervention records linked to support episodes.
- [ ] Run: `uv run pytest tests/storage/test_support_intervention_storage.py::test_support_interventions_round_trip_through_sqlite_store -v`

### Arc and context query surfaces

- [ ] Test: `test_sqlite_store_lists_support_interventions_by_arc_and_context()` - verify intervention records can be queried for one arc or one context in deterministic order.
- [ ] Implement: add minimal query helpers that filter persisted interventions by `arc_id` and `context` without introducing runtime compiler logic.
- [ ] Run: `uv run pytest tests/storage/test_support_intervention_storage.py::test_sqlite_store_lists_support_interventions_by_arc_and_context -v`

### Applied-dimension query surface

- [ ] Test: `test_sqlite_store_lists_support_interventions_by_applied_dimension()` - verify Alfred can find interventions that used a specific relational or support dimension.
- [ ] Implement: add the smallest persisted dimension index or lookup path needed to query intervention records by applied dimension while preserving the validated typed record as the source of truth.
- [ ] Run: `uv run pytest tests/storage/test_support_intervention_storage.py::test_sqlite_store_lists_support_interventions_by_applied_dimension -v`

---

## Files to Modify

1. `src/alfred/memory/support_memory.py` - add the typed support intervention model and any shared provenance types needed by callers
2. `src/alfred/memory/__init__.py` - re-export intervention types if callers need the package surface
3. `src/alfred/storage/sqlite.py` - add intervention tables, indexes, and save/load/query helpers
4. `tests/test_support_intervention.py` - contract and record-round-trip tests for intervention logs
5. `tests/storage/test_support_intervention_storage.py` - SQLite round-trip and query-surface tests

## Commit Strategy

Each completed test → implement → run block should map cleanly to one atomic commit:
- `feat(memory): add support intervention contract`
- `feat(memory): serialize support intervention records`
- `feat(storage): store support interventions in sqlite`
- `feat(storage): query support interventions by arc and context`
- `feat(storage): query support interventions by applied dimension`
