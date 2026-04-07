# Execution Plan: PRD #169 - Milestone 1 Reflection Contracts

## Overview
Define the contract-first foundation for PRD #169 without adding UI surfaces or live reflection behavior yet. This slice adds derived review-card schemas on top of durable patterns, the hybrid inspection read models they depend on, and typed correction actions that allow pattern confirmation/rejection plus profile-value edits only.

## Current Repo Constraints
- PRD #168 already ships durable `LearningSituation`, `SupportPattern`, and `SupportProfileUpdateEvent` contracts in `src/alfred/memory/support_learning.py`. Milestone 1 must build on those objects rather than creating a second pattern truth layer.
- `src/alfred/storage/sqlite.py` is already the persistence boundary for support memory, support profile values, learning situations, patterns, and update events. It has point lookups plus runtime pattern loading, but it does not yet expose the list and detail queries needed for reflection inspection.
- `src/alfred/support_policy.py` already resolves effective runtime behavior from stored support-profile values plus confirmed patterns. The inspection surface must read from the same source of truth instead of recomputing parallel state.
- `SupportEpisode` remains a derived report boundary. Reflection contracts should point back to learning situations, patterns, and update events rather than making episodes the primary learning unit again.
- No `orchestration/` package exists in the repo. If a new module is needed, keep it small and adjacent to the current support runtime modules.
- The user chose v1 correction flows where patterns can be confirmed or rejected, but only support-profile values can be corrected, reset, or scope-limited. Direct editing of pattern claim text is out of scope.

## Success Signal
- Alfred can derive typed review cards from durable patterns without creating a parallel truth system.
- Callers can request one inspection snapshot that combines current help state and learned state from the same underlying sources runtime already uses, then drill into pattern, update-event, and effective-value details as needed.
- Correction requests are represented as typed, auditable actions that support pattern confirmation/rejection and profile-value correction/reset/scope-limiting while making pattern-text editing impossible in v1.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/test_support_reflection.py tests/storage/test_support_reflection_storage.py`
- **Typing:** `uv run mypy --strict src/`
- **Targeted tests for this phase:** `uv run pytest tests/test_support_reflection.py tests/storage/test_support_reflection_storage.py -v`

---

## Phase 1: Review-card contract

### Derived review cards from durable patterns

- [x] Test: `test_review_card_derives_from_support_pattern_without_creating_parallel_truth()` - verify each durable pattern kind maps to one typed review card, preserves scope/status/confidence, carries bounded evidence refs, and retains a link to the source pattern instead of duplicating durable truth.
- [x] Implement: add typed review-card contracts plus a pattern-to-card derivation helper in a small reflection contract module.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_review_card_derives_from_support_pattern_without_creating_parallel_truth -v`

### Card validation stays bounded

- [x] Test: `test_review_card_rejects_unknown_card_kinds_and_missing_next_actions()` - verify cards accept only the fixed v1 card kinds and require a practical next action, confirmation question, or correction step.
- [x] Implement: add validation for the bounded v1 card surface so the reflection layer cannot emit generic or actionless cards.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_review_card_rejects_unknown_card_kinds_and_missing_next_actions -v`

---

## Phase 2: Inspection storage queries

### Reflection inspection list queries

- [x] Test: `test_support_reflection_storage_lists_patterns_for_inspection_and_recent_update_events()` - verify SQLite can list candidate and confirmed patterns plus recent support-profile update events in deterministic order for inspection flows.
- [x] Implement: add the minimal SQLite list helpers needed for inspection summaries without reusing the narrower runtime-only pattern query.
- [x] Run: `uv run pytest tests/storage/test_support_reflection_storage.py::test_support_reflection_storage_lists_patterns_for_inspection_and_recent_update_events -v`

### Reflection inspection detail queries

- [x] Test: `test_support_reflection_storage_returns_pattern_and_update_event_details_for_drilldowns()` - verify inspection drill-downs can load the durable pattern and update-event records behind one summary item.
- [x] Implement: reuse or add the minimal SQLite detail helpers required for pattern and update-event drill-downs.
- [x] Run: `uv run pytest tests/storage/test_support_reflection_storage.py::test_support_reflection_storage_returns_pattern_and_update_event_details_for_drilldowns -v`

---

## Phase 3: Hybrid inspection read models

### One snapshot combines current help state and learned state

- [x] Test: `test_support_inspection_snapshot_reads_runtime_and_learned_state_from_one_source_of_truth()` - verify one inspection snapshot includes effective support values, effective relational values, active runtime-relevant patterns, candidate patterns, confirmed patterns, and recent update events for a requested response mode and optional arc.
- [x] Implement: add `SupportInspectionSnapshot` and related summary models, built from the same stored values and pattern inputs the runtime resolver already uses.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_inspection_snapshot_reads_runtime_and_learned_state_from_one_source_of_truth -v`

### Drill-down explanations stay explicit and bounded

- [x] Test: `test_support_inspection_drilldowns_explain_pattern_update_event_and_effective_value_details()` - verify callers can request pattern detail, update-event detail, and an explanation of why one effective value is currently winning for a given runtime request.
- [x] Implement: add bounded drill-down read models and the minimal explanation helper for effective values.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_inspection_drilldowns_explain_pattern_update_event_and_effective_value_details -v`

---

## Phase 4: Typed correction action contracts

### Actions allow pattern confirmation and profile-value edits only

- [x] Test: `test_support_correction_actions_allow_pattern_confirmation_and_profile_value_edits_only()` - verify the v1 action surface supports confirm/reject for patterns and correct/reset/scope-limit for profile values, while direct pattern-text editing is unrepresentable or rejected.
- [x] Implement: add typed correction-action contracts and validation for allowed targets, scopes, and required payload fields.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_correction_actions_allow_pattern_confirmation_and_profile_value_edits_only -v`

### Correction actions stay auditable

- [x] Test: `test_support_correction_actions_capture_auditable_targets_and_requested_scope_changes()` - verify each action preserves the durable target identity, requested new scope when applicable, and the reason payload needed for later traceable application.
- [x] Implement: tighten the action contracts so later mutation flows can apply them without guessing target shape or audit metadata.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_support_correction_actions_capture_auditable_targets_and_requested_scope_changes -v`

---

## Phase 5: Milestone proof

### Reflection contracts keep truth classes clean

- [x] Test: `test_reflection_contracts_keep_patterns_durable_cards_derived_and_value_edits_auditable()` - verify one stored pattern and one recent update event can produce a review card, appear in an inspection snapshot, and expose only the allowed correction actions without collapsing runtime truth, learned truth, and reflection output into one object.
- [x] Implement: tighten any remaining shared helpers until the contract boundaries hold across the full Milestone 1 slice.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_reflection_contracts_keep_patterns_durable_cards_derived_and_value_edits_auditable -v`

---

## Files to Modify

1. `src/alfred/support_reflection.py` - review-card contracts, inspection read models, and typed correction actions
2. `src/alfred/storage/sqlite.py` - inspection list/detail queries for patterns and update events
3. `src/alfred/support_policy.py` - shared effective-value explanation or resolver seam reuse if needed
4. `src/alfred/memory/__init__.py` - export the new reflection contracts if they become public repo surfaces
5. `tests/test_support_reflection.py` - review-card, inspection, correction-action, and milestone-proof tests
6. `tests/storage/test_support_reflection_storage.py` - SQLite inspection query tests
7. `prds/done/169-reflection-reviews-and-support-controls.md` - sync milestone wording and decisions as this slice lands
8. `prds/done/execution-plan-169-milestone1.md` - track progress through the contract-first slice

## Commit Strategy

Each completed test -> implement -> run block should map cleanly to one atomic commit:
- `feat(reflection): add review card contracts`
- `feat(storage): add reflection inspection queries`
- `feat(reflection): add inspection snapshot models`
- `feat(reflection): add correction action contracts`
- `test(reflection): prove reflection contract boundaries`
