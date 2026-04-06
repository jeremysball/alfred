# Execution Plan: PRD #169 - Milestones 2 and 6 Reflection Surfacing

## Overview
Implement the deterministic reflection-loading and surfacing rules that sit between durable patterns and live conversation. This slice adds pattern load scoring, move-impact and surface-level decisions, and runtime prompt guidance for inline reflection and bounded session-start surfacing.

## Current Repo Constraints
- `src/alfred/support_policy.py` already owns turn assessment, response-mode derivation, runtime value resolution, and the compiled support contract. Reflection surfacing should reuse that runtime result instead of re-classifying the turn from scratch in a second subsystem.
- `src/alfred/support_reflection.py` now owns derived review-card, inspection, and correction contracts. The live surfacing engine should extend that module rather than inventing a separate orchestration package.
- Durable patterns are stored in `support_patterns`, but only confirmed patterns currently affect runtime values. Candidate patterns may be surfaced for review or reflective continuity, but they should not silently become runtime truth.
- Pattern records point back to supporting learning-situation IDs rather than carrying their own embeddings. Semantic relevance for live surfacing must therefore reuse similar-situation retrieval rather than inventing a second embedding store for patterns.
- `Alfred.chat_stream()` already appends the runtime support contract into the final system prompt. Reflection surfacing should use the same injection seam and keep policy semantics product-owned while phrasing stays natural/model-owned.
- Session-start surfacing must stay bounded to at most 1-2 patterns and must not derail execution-oriented starts into essays.

## Success Signal
- Alfred can load relevant patterns silently for live turns and surface only the small subset whose removal would materially change the next move.
- Session-start surfacing chooses bounded pattern priorities that match the current start type: operational starts favor blocker/support-fit continuity, reflective starts favor identity/direction themes, and calibration starts favor contradiction.
- The final system prompt can carry a bounded reflection-guidance section alongside the support contract when a pattern should be surfaced, while ordinary turns stay silent.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/alfred/support_reflection.py src/alfred/alfred.py tests/test_support_reflection.py tests/test_core_observability.py`
- **Typing:** `uv run mypy --strict src/alfred/support_reflection.py src/alfred/alfred.py`
- **Targeted tests for this phase:** `uv run pytest tests/test_support_reflection.py tests/test_core_observability.py -v`

---

## Phase 1: Pattern load and move-impact rules

### Deterministic load decisions

- [x] Test: `test_reflection_runtime_loads_relevant_patterns_silently_before_considering_surfacing()` - verify confirmed and candidate patterns can be scored for one live turn using scope, supporting-situation overlap, recency, and status without surfacing everything by default.
- [x] Implement: add load-scoring helpers and bounded load decisions in `src/alfred/support_reflection.py`.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_reflection_runtime_loads_relevant_patterns_silently_before_considering_surfacing -v`

### Move-impact classification

- [x] Test: `test_reflection_runtime_distinguishes_silent_compact_and_richer_surface_levels()` - verify the same loaded pattern set can be classified into silent, compact, or richer surfacing based on how much it changes the current move.
- [x] Implement: add move-impact and surface-level rules that stay deterministic and bounded.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_reflection_runtime_distinguishes_silent_compact_and_richer_surface_levels -v`

---

## Phase 2: Session-start priority rules

### Start-type priority ordering

- [x] Test: `test_reflection_runtime_prioritizes_operational_reflective_and_calibration_starts_differently()` - verify fresh-session starts prefer support-fit/blocker patterns for operational turns, identity/direction themes for reflective turns, and calibration gaps for calibration turns.
- [x] Implement: add the session-start type classifier and priority tables in the reflection runtime.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_reflection_runtime_prioritizes_operational_reflective_and_calibration_starts_differently -v`

### Fresh-session boundedness

- [x] Test: `test_reflection_runtime_caps_session_start_surfacing_to_two_patterns()` - verify even when several patterns are relevant, the reflection runtime surfaces at most two and leaves the rest silent.
- [x] Implement: add bounded selection logic for fresh-session surfacing.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_reflection_runtime_caps_session_start_surfacing_to_two_patterns -v`

---

## Phase 3: Prompt integration

### Reflection prompt section is appended only when needed

- [x] Test: `test_chat_stream_appends_reflection_guidance_only_when_a_pattern_should_be_surfaced()` - verify the final system prompt gains a bounded reflection-guidance section when the turn merits it and stays unchanged otherwise.
- [x] Implement: reuse the existing support-policy runtime seam in `Alfred.chat_stream()` to append a rendered reflection section after the support contract.
- [x] Run: `uv run pytest tests/test_core_observability.py::test_chat_stream_appends_reflection_guidance_only_when_a_pattern_should_be_surfaced -v`

### Prompt wording keeps policy internal

- [x] Test: `test_reflection_prompt_guidance_stays_natural_and_hides_internal_labels()` - verify the rendered reflection section steers surfacing behavior without exposing policy labels, score names, or internal metadata.
- [x] Implement: add the bounded reflection renderer and tighten wording for natural realization.
- [x] Run: `uv run pytest tests/test_support_reflection.py::test_reflection_prompt_guidance_stays_natural_and_hides_internal_labels -v`

---

## Files to Modify

1. `src/alfred/support_reflection.py` - pattern load scoring, move-impact rules, session-start selection, and prompt rendering
2. `src/alfred/alfred.py` - append reflection guidance alongside the support contract at runtime
3. `tests/test_support_reflection.py` - load, surface-level, and session-start priority tests
4. `tests/test_core_observability.py` - prompt-injection integration test for reflection guidance
5. `prds/169-reflection-reviews-and-support-controls.md` - sync progress and decision wording as this slice lands
6. `prds/execution-plan-169-milestone2.md` - track milestone progress

## Commit Strategy

Each completed test -> implement -> run block should map cleanly to one atomic commit:
- `feat(reflection): add pattern load scoring`
- `feat(reflection): add session-start surfacing rules`
- `feat(core): append reflection guidance to live prompts`
