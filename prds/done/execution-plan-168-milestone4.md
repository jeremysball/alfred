# Execution Plan: PRD #168 - Milestone 4: Add Turn Assessment, Policy Resolvers, and the Behavior Compiler

## Overview
This phase turns stored support-profile values and intervention history into a runtime control plane. It adds a small support-policy module that first assesses the live turn into one `need` plus ordered `subjects[]`, then derives a `response_mode` using Alfred's existing context taxonomy, resolves effective support and relational values from runtime inputs, compiles them into an explicit response contract, and injects that contract into Alfred's live prompt before the LLM runs. It stops short of bounded adaptation and the broader docs or template refresh reserved for later milestones.

## Current Repo Constraints
- `src/alfred/storage/sqlite.py` already resolves one stored support-profile value by `arc -> context -> global` precedence, but it does not compose authored defaults, transient adjustments, or pattern inputs across dimensions.
- `src/alfred/alfred.py` passes one flat `system_prompt` string into `Agent.run()` and `Agent.run_stream()`. Milestone 4 must fit the compiled contract into that existing seam instead of inventing a new provider protocol.
- `src/alfred/context.py` assembles mostly static markdown context plus memories and session history. Because the behavior contract is turn-specific, runtime injection should happen after context assembly rather than by mutating managed template files.
- `src/alfred/memory/support_context.py` already detects strong resume and broad orientation fresh-session openings, but there is no general runtime turn-assessment contract yet for `orient`, `resume`, `activate`, `decide`, `reflect`, and `calibrate`.
- The public assessment contract should stay small: one `need` plus ordered `subjects[]`. Richer cue matches, feature values, confidence math, dropped candidates, and relation details belong in internal trace rather than the prompt-facing runtime contract.
- Need assessment should use the existing local embedding infrastructure with centroid scoring plus top-`k` exemplar support rather than raw phrase weighting alone.
- The live turn should be embedded once and reused for both need assessment and subject resolution.
- Subject assessment should use embeddings for candidate recall across all subject kinds, then apply deterministic grounding, threshold, and ambiguity gates before emitting ordered `subjects[]`.
- Milestone 4 v1 should not use a need-to-subject compatibility matrix.
- `response_mode` should be derived after assessment and should reuse the existing context-ID taxonomy (`plan`, `execute`, `decide`, `review`, `identity_reflect`, `direction_reflect`) rather than inventing a new routing vocabulary.
- `domain` is a valid subject kind for turn assessment, but this milestone should not add domain-scoped support-profile persistence or precedence. Domain subjects narrow retrieval and framing only.
- V1 turn assessment returns exactly one need, may return `unknown`, and may emit zero or more ordered subjects. It should use live-turn evidence only: latest user message, recent in-session turns, fresh-session status, current session state, active arc already in scope, and candidate arc/domain matches. It should not depend on persisted recent episodes or intervention history.
- Fresh-session detection should not depend on brittle contiguous phrase matches alone. Milestone 4 should prefer small deterministic scored heuristics over exact-string classification and keep an explicit unknown path.
- The repo has no `orchestration/` package today. This milestone should introduce one small runtime module, not a broad new subsystem.
- Stance labels must remain derived summaries from resolved relational values. Milestone 4 should not add hard-coded persona modes.
- This phase must stop at runtime resolution and compilation. It should not silently auto-update support profiles or widen into Milestone 5 adaptation work.

## Success Signal
- Given representative live turns, Alfred emits a small turn assessment with exactly one `need` and zero or more ordered `subjects[]`, without forcing brittle guesses when the need is unclear.
- Alfred maps that assessment to one `response_mode` using the existing context-ID taxonomy, including a neutral `execute` fallback for `unknown` need.
- Given representative runtime inputs, Alfred resolves effective support and relational values from authored defaults, stored scoped learning, transient state, and selected patterns without leaving registry bounds.
- Alfred compiles those values into an explicit response contract with a derived stance summary plus compiler-only fields such as `evidence_mode` and `intervention_family`.
- Before the LLM runs, `Alfred.chat_stream()` injects the compiled contract into the final system prompt so generation is constrained by runtime-owned policy rather than prompt style alone.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/test_support_policy.py tests/test_core_observability.py` and `uv run mypy --strict src/`
- **Targeted tests for this phase:** `uv run pytest tests/test_support_policy.py tests/test_core_observability.py -v`

---

## Phase 1: Milestone 4 - Add turn assessment, policy resolvers, and the behavior compiler

### Turn assessment contract

- [x] Test: `test_support_turn_assessment_returns_one_need_and_ordered_subjects()` - verify the assessor embeds the live turn once, uses centroid scoring plus top-`k` support for `need`, uses embedding-based subject candidate recall plus deterministic grounding for `subjects[]`, and returns exactly one `need` with ordered grounded subjects in the public contract.
- [x] Implement: add a small turn assessor that embeds the live turn once, applies deterministic abstention rules for `need`, applies deterministic grounding and ambiguity gates for `subjects[]`, and keeps richer similarity, candidate, and fallback details in internal trace.
- [x] Run: `uv run pytest tests/test_support_policy.py::test_support_turn_assessment_returns_one_need_and_ordered_subjects -v`

### Unknown fallback and response-mode mapping

- [x] Test: `test_support_response_mode_maps_unknown_and_subject_aware_assessments_to_existing_context_ids()` - verify `unknown` need falls back to neutral `execute`, while representative resume, reflect, and calibrate assessments map to the correct existing response modes.
- [x] Implement: derive `response_mode` from the public assessment in a separate mapper that reuses the existing context-ID taxonomy and does not bloat the assessor contract.
- [x] Run: `uv run pytest tests/test_support_policy.py::test_support_response_mode_maps_unknown_and_subject_aware_assessments_to_existing_context_ids -v`

### Composite value resolution

- [x] Test: `test_support_policy_resolver_combines_defaults_scopes_patterns_and_transient_state()` - verify the resolver starts from authored defaults, uses derived `response_mode`, prefers arc, then context, then global learned values, applies representative transient and pattern-based adjustments, and clamps to registry bounds.
- [x] Implement: add a runtime policy resolver that composes effective support and relational values from PRD-backed defaults plus stored scoped values, transient inputs, selected patterns, and resolved subjects.
- [x] Run: `uv run pytest tests/test_support_policy.py::test_support_policy_resolver_combines_defaults_scopes_patterns_and_transient_state -v`

### Behavior contract compilation

- [x] Test: `test_support_behavior_contract_derives_stance_evidence_mode_and_intervention_family()` - verify resolved values compile into explicit runtime-owned fields, a readable derived stance summary, and compiler-only decisions for representative activate and calibrate cases.
- [x] Implement: add a typed `SupportBehaviorContract` compiler that derives stance labels, `evidence_mode`, and `intervention_family` without introducing hard-coded persona modes.
- [x] Run: `uv run pytest tests/test_support_policy.py::test_support_behavior_contract_derives_stance_evidence_mode_and_intervention_family -v`

### Runtime application before generation

- [x] Test: `test_chat_stream_includes_compiled_support_contract_in_system_prompt()` - verify `Alfred.chat_stream()` builds the assessment, derives `response_mode`, resolves effective values, and injects the compiled contract into the final system prompt before `agent.run_stream()` is called.
- [x] Implement: add the thinnest Alfred-side integration that appends one explicit support-contract section to the final system prompt after context assembly.
- [x] Run: `uv run pytest tests/test_core_observability.py::test_chat_stream_includes_compiled_support_contract_in_system_prompt -v`

### Milestone proof across representative contexts

- [x] Test: `test_support_behavior_contract_changes_across_operational_reflective_and_calibration_contexts()` - verify representative execute, direction-reflect, and review or calibration inputs produce meaningfully different contracts rather than one generic prompt fragment.
- [x] Implement: tighten defaults and mapping tables until the public contract surface matches the PRD's context-sensitive policy table in representative scenarios.
- [x] Run: `uv run pytest tests/test_support_policy.py::test_support_behavior_contract_changes_across_operational_reflective_and_calibration_contexts -v`

---

## Files to Modify

1. `src/alfred/support_policy.py` - new turn-assessment, response-mode mapping, resolver, and behavior-compiler module
2. `src/alfred/alfred.py` - inject the compiled contract before agent execution
3. `tests/test_support_policy.py` - turn-assessment, response-mode mapping, resolver, compiler, and representative-context tests
4. `tests/test_core_observability.py` - runtime seam test proving the compiled contract reaches the agent
5. `src/alfred/memory/support_context.py` - only if the assessor needs one small shared seam for resume and orientation detection

## Commit Strategy

Each completed test -> implement -> run block should map cleanly to one atomic commit:
- `feat(policy): assess support turns`
- `feat(policy): map support response modes`
- `feat(policy): resolve composite support values`
- `feat(policy): compile support behavior contract`
- `feat(core): apply support contract before generation`
- `test(policy): prove representative runtime contracts`
