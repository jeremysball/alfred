# Execution Plan: PRD #168 - Milestone 5 Bounded Adaptation

## Overview
Implement the learning core behind bounded adaptation: generalized learning situations, first-class patterns, durable support-profile update events, embedding-based similar-situation retrieval, bounded auto-updates for low-risk scopes, and runtime loading of pattern inputs alongside support-profile values.

## Current Repo Constraints
- `src/alfred/storage/sqlite.py` is the persistence boundary for support memory, support profile, and vector-backed retrieval.
- `src/alfred/support_policy.py` already owns turn assessment, response-mode derivation, policy resolution, and prompt-facing contract compilation.
- `SupportIntervention` already exists and should remain the atomic action log; Milestone 5 must not overload it into the only learning abstraction.
- `SupportEpisode` already exists in storage and support-context code. Under the updated product model it should remain a derived report/synthesis surface, not the primary similarity or adaptation container.
- The repo already has sqlite-vec integration and message-embedding storage. Milestone 5 should reuse the local embedding infrastructure rather than inventing fake NLP heuristics.
- Broad identity and direction claims must remain candidate-first and reviewable; Milestone 5 should not silently promote them into durable truth.
- Runtime pattern influence must stay within registry bounds. Patterns may change behavior, but they must not bypass support-profile validation.
- The thinnest runtime integration seam remains `SupportPolicyRuntime` / `resolve_support_policy()` and the existing `Alfred.chat_stream()` flow.

## Success Signal
- Alfred can persist and retrieve generalized learning situations with embeddings, linked interventions, and outcome evidence.
- Given a live turn, Alfred can retrieve semantically similar prior situations across arcs when the similarity is strong enough.
- Alfred can derive and persist first-class patterns plus durable support-profile update events from matched situations.
- Low-risk arc and context support values can auto-update with evidence, while broader changes remain surfaced as candidate patterns or reviewable update events instead of silently becoming active truth.
- Runtime policy resolution uses both persisted support-profile values and active pattern inputs to change the next move.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/test_support_learning.py tests/storage/test_support_learning_storage.py tests/test_support_policy.py` and `uv run mypy --strict src/`
- **Targeted tests for this phase:** `uv run pytest tests/test_support_learning.py tests/storage/test_support_learning_storage.py tests/test_support_policy.py -v`

---

## Phase 1: Learning-situation contract and storage

### Generalized learning-situation record

- [x] Test: `test_learning_situation_round_trips_with_embedding_contract_and_linked_interventions()` - verify one learning situation preserves turn shape, embedding, linked intervention IDs, signals, and evidence through the durable contract.
- [x] Implement: add a typed `LearningSituation` model plus serialization helpers and public exports.
- [x] Run: `uv run pytest --no-cov -p no:cacheprovider tests/test_support_learning.py::test_learning_situation_round_trips_with_embedding_contract_and_linked_interventions -v`

### SQLite persistence and retrieval

- [x] Test: `test_learning_situation_storage_round_trips_and_lists_recent_situations()` - verify SQLite saves and loads learning situations in stable chronological order without losing linked intervention IDs or embeddings.
- [x] Implement: add learning-situation tables and storage methods in `src/alfred/storage/sqlite.py`.
- [x] Run: `uv run pytest --no-cov -p no:cacheprovider tests/storage/test_support_learning_storage.py::test_learning_situation_storage_round_trips_and_lists_recent_situations -v`

### Similar-situation retrieval

- [x] Test: `test_similar_learning_situations_can_match_across_arcs_when_semantics_are_strong()` - verify vector retrieval can surface a semantically similar prior situation from another arc while preserving similarity ordering and structured filters.
- [x] Implement: add vec-backed similar-situation search with structured constraints such as response mode and need.
- [x] Run: `uv run pytest --no-cov -p no:cacheprovider tests/storage/test_support_learning_storage.py::test_similar_learning_situations_can_match_across_arcs_when_semantics_are_strong -v`

---

## Phase 2: Pattern and update-event contracts

### First-class pattern records

- [x] Test: `test_support_pattern_round_trips_with_kind_scope_status_and_supporting_situations()` - verify a durable pattern preserves kind, claim, scope, status, confidence, and supporting learning situations.
- [x] Implement: add a typed support-pattern model and SQLite persistence surface.
- [x] Run: `uv run pytest --no-cov -p no:cacheprovider tests/test_support_learning.py::test_support_pattern_round_trips_with_kind_scope_status_and_supporting_situations -v`

### Reviewable profile update events

- [x] Test: `test_support_profile_update_event_round_trips_old_new_values_and_evidence()` - verify update events store the target change, rationale, and evidence needed for reversibility.
- [x] Implement: add a typed support-profile update-event model and SQLite persistence surface.
- [x] Run: `uv run pytest --no-cov -p no:cacheprovider tests/storage/test_support_learning_storage.py::test_support_profile_update_event_round_trips_old_new_values_and_evidence -v`

---

## Phase 3: Bounded adaptation engine

### Low-risk scoped auto-updates

- [x] Test: `test_bounded_adaptation_auto_updates_arc_and_context_support_values_from_similar_successful_situations()` - verify repeated strong matched situations can directly update low-risk arc/context support-profile values with evidence and logged update events.
- [x] Implement: add the bounded adaptation engine plus persistence helper that reads similar situations, derives low-risk updates, saves the current learning situation, persists the updated support-profile value, and logs the update event.
- [x] Run: `uv run pytest --no-cov -p no:cacheprovider tests/test_support_learning.py::test_bounded_adaptation_auto_updates_arc_and_context_support_values_from_similar_successful_situations -v`

### Broader changes stay surfaced

- [x] Test: `test_bounded_adaptation_surfaces_broader_changes_as_patterns_or_reviewable_candidates()` - verify broader support or relational changes do not silently auto-promote and instead persist candidate patterns or reviewable update events.
- [x] Implement: add stronger thresholds and truth-class guards so broader relational changes surface as candidate patterns or proposed update events instead of silently becoming active truth.
- [x] Run: `uv run pytest --no-cov -p no:cacheprovider tests/test_support_learning.py::test_bounded_adaptation_surfaces_broader_changes_as_patterns_or_reviewable_candidates -v`

---

## Phase 4: Runtime consumption of learned patterns

### Pattern-aware runtime resolution

- [x] Test: `test_support_policy_runtime_loads_active_patterns_and_support_profile_values_together()` - verify runtime policy resolution uses active patterns as co-equal inputs alongside stored scoped profile values to change the compiled contract.
- [x] Implement: load active patterns from storage for the current turn and pass them through the existing resolver without breaking registry validation.
- [x] Run: `uv run pytest --no-cov -p no:cacheprovider tests/test_support_policy.py::test_support_policy_runtime_loads_active_patterns_and_support_profile_values_together -v`

### Milestone proof

- [x] Test: `test_support_learning_core_links_intervention_situation_pattern_and_update_event_without_episode_ownership()` - verify one end-to-end learning slice can connect an intervention, a learning situation, a resulting pattern or profile update event, and a changed future contract while keeping episodes out of the primary write path.
- [x] Implement: tighten the write path until the learning core uses situations first, persists adaptation artifacts together, and leaves episodes as derived reports.
- [x] Run: `uv run pytest --no-cov -p no:cacheprovider tests/test_support_learning.py::test_support_learning_core_links_intervention_situation_pattern_and_update_event_without_episode_ownership -v`

---

## Files to Modify

1. `src/alfred/memory/support_learning.py` - new learning-situation, pattern, and update-event contracts
2. `src/alfred/memory/__init__.py` - export the new learning contracts
3. `src/alfred/storage/sqlite.py` - persistence, vec-backed retrieval, and update-event storage
4. `src/alfred/support_policy.py` - pattern loading and pattern-aware runtime resolution
5. `tests/test_support_learning.py` - learning contract and bounded adaptation tests
6. `tests/storage/test_support_learning_storage.py` - SQLite storage and similarity retrieval tests
7. `tests/test_support_policy.py` - runtime pattern-loading proof
8. `prds/168-adaptive-support-profile-and-intervention-learning.md` - decision and progress updates as slices land

## Commit Strategy

Each completed test -> implement -> run block should map cleanly to one atomic commit:
- `feat(memory): add learning situation contract`
- `feat(storage): store support learning situations`
- `feat(storage): retrieve similar support situations`
- `feat(memory): add support patterns and update events`
- `feat(policy): add bounded adaptation engine`
- `feat(policy): load runtime support patterns`
- `test(policy): prove situation-first learning flow`
