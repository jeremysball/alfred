# Execution Plan: PRD #183 - Milestone 2: Reply-time SupportAttempt writes with real refs

## Overview
Land the first live v2 runtime write without pretending the full learning runtime is already case-based. This phase captures one `SupportAttempt` per reply using the real persisted session, user-message, and assistant-message references from `chat_stream()`, while leaving v1 `LearningSituation`-based bounded adaptation in place until later milestones replace it.

## Current Repo Constraints
- `src/alfred/alfred.py` currently asks `SupportPolicyRuntime.build_turn_contract()` for the prompt contract before generation, but it does not preserve the returned runtime result long enough to persist a v2 attempt after the assistant reply is finalized.
- `SupportAttempt` persistence requires real `session_id`, `user_message_id`, and `assistant_message_id` refs. `src/alfred/storage/sqlite.py` now enforces that contract against persisted session-message rows instead of tolerating fabricated placeholders.
- In the normal non-streaming-persist path, `chat_stream()` currently background-persists final session messages via `_spawn_persist_task()`. That means a v2 attempt cannot be saved immediately unless the required message rows are durably written first.
- `src/alfred/support_policy.py` still persists v1 `LearningSituation` rows during `build_turn_contract()`. Milestone 2 must keep that behavior working while adding the first live v2 write.
- The public seam for this milestone is the reply path, not raw storage helpers. The tests should prove that a real chat turn produces one durable `SupportAttempt` with real refs.

## Success Signal
- A live `chat_stream()` turn with support runtime enabled persists one `SupportAttempt` row with the real session id plus the actual user and assistant message ids for that turn.
- The saved attempt preserves the need, response mode, subject refs, effective support values, effective relational values, and intervention family from the runtime result that shaped the reply.
- Attempt persistence runs only after the required session-message rows exist, so the v2 store never falls back to fake ids like `session_id="runtime"`.
- The existing v1 bounded-adaptation write path still runs until later milestones replace it.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/test_support_policy.py tests/test_core_observability.py` and `uv run mypy --strict src/`
- **Targeted tests:** run the smallest pytest command listed under each task

---

## Phase 1: Runtime attempt record contract

### Build one `SupportAttempt` from the runtime result

- [ ] Test: `test_support_policy_runtime_builds_v2_support_attempt_from_runtime_result()` in `tests/test_support_policy.py` — verify the runtime can derive one typed `SupportAttempt` from the reply-time runtime result plus real refs without losing subject refs, active scope, effective values, or contract summary.
- [ ] Implement: add the minimal helper(s) in `src/alfred/support_policy.py` that turn a `SupportPolicyRuntimeResult` plus real ids into a `SupportAttempt`, without changing the existing v1 bounded-adaptation logic.
- [ ] Run: `uv run pytest tests/test_support_policy.py::test_support_policy_runtime_builds_v2_support_attempt_from_runtime_result -v`

### Persist the attempt from the public reply seam

- [ ] Test: `test_chat_stream_persists_v2_support_attempt_with_real_refs()` in `tests/test_core_observability.py` — verify a real `chat_stream()` turn preserves the runtime result, persists the backing session messages, and then writes exactly one `SupportAttempt` with real user/assistant ids.
- [ ] Implement: thread the runtime result through `src/alfred/alfred.py`, ensure the final reply path persists the required session-message rows before saving the attempt, and call the new support-runtime helper so reply-time attempt capture is durable.
- [ ] Run: `uv run pytest tests/test_core_observability.py::test_chat_stream_persists_v2_support_attempt_with_real_refs -v`

---

## Final phase verification

- [ ] Run: `uv run ruff check src/ tests/test_support_policy.py tests/test_core_observability.py`
- [ ] Run: `uv run mypy --strict src/`
- [ ] Run: `uv run pytest tests/test_support_policy.py tests/test_core_observability.py -v`

## Files to Modify

1. `src/alfred/support_policy.py` - derive typed v2 `SupportAttempt` records from runtime results
2. `src/alfred/alfred.py` - preserve the runtime result through reply finalization and persist the attempt after real message refs exist
3. `tests/test_support_policy.py` - add the runtime-to-attempt contract test
4. `tests/test_core_observability.py` - add the public reply-seam persistence test
5. `prds/execution-plan-183-milestone1.md` - keep the Milestone 1 deferral note aligned

## Commit Strategy

Each completed test → implement → run block should map to one atomic commit:
- `refactor(support): build v2 support attempts from runtime results`
- `feat(runtime): persist v2 support attempts from chat turns`
