# Execution Plan: PRD #168 - Milestone 6 Regression Coverage, Documentation, and Prompt/Template Updates

## Overview
Close PRD #168 by tightening the last behavioral boundary around the runtime support contract, then sync the managed docs and prompt templates to the situation-first learning model already implemented in Milestone 5. This milestone is intentionally small: it should prove that runtime policy remains product-owned while the model still phrases responses naturally, and it should remove stale episode-first wording from the human-facing docs/templates.

## Current Repo Constraints
- `src/alfred/support_policy.py` already renders the prompt-facing runtime support contract that gets appended in `Alfred.chat_stream()`.
- The remaining open success criterion is behavioral, not architectural: the runtime must own policy without forcing rigid stock wording or leaking internal metadata into normal replies.
- `templates/SYSTEM.md` is the managed prompt source of truth for Alfred's durable operating instructions and must stay aligned with the implemented support-learning model.
- `docs/relational-support-model.md` still carries older episode-first learning language in places and must be updated to match the implemented `LearningSituation` model.
- Milestone 6 should stay narrow. It should not redesign the runtime contract, reflection UX, or storage model.

## Success Signal
- The rendered runtime support contract explicitly tells the model to realize the move naturally rather than parroting metadata.
- The managed prompt/template content says the runtime contract shapes behavior while the model owns phrasing.
- The architectural docs describe learning situations as the primary adaptation/matching unit and episodes as derived review/report surfaces.
- PRD #168 status and execution plan history clearly show Milestone 6 as the final cleanup slice rather than leaving the last success criterion ambiguous.

## Validation Workflow
- **Workflow:** Python + docs/templates
- **Static checks:** `uv run ruff check src/alfred/support_policy.py tests/test_support_policy.py`
- **Targeted tests for this phase:** `uv run pytest --no-cov -p no:cacheprovider tests/test_support_policy.py -v`
- **Docs/template verification:** inspect `templates/SYSTEM.md`, `docs/relational-support-model.md`, and `prds/168-adaptive-support-profile-and-intervention-learning.md` for situation-first wording and the phrasing-vs-policy boundary.

---

## Phase 1: Prompt-boundary regression

### Natural phrasing remains model-owned

- [x] Test: `test_support_policy_runtime_builds_prompt_section_from_runtime_components()` - verify the rendered runtime support contract keeps the semantic policy fields while explicitly instructing the model to express the response naturally and avoid surfacing internal labels by default.
- [x] Implement: extend `render_support_behavior_contract()` with one compact realization rule that keeps policy product-owned and phrasing model-owned.
- [x] Run: `uv run pytest --no-cov -p no:cacheprovider tests/test_support_policy.py::test_support_policy_runtime_builds_prompt_section_from_runtime_components -v`

## Phase 2: Docs and managed template alignment

### Situation-first learning language

- [x] Implement: update `docs/relational-support-model.md` so learning situations are the primary learning/matching unit and episodes are derived synthesis/report surfaces.
- [x] Implement: update `templates/SYSTEM.md` so the managed system prompt reflects the same situation-first learning model and explicitly keeps internal policy labels out of normal replies unless the user asks.
- [x] Verify: read the updated docs/templates and confirm they match the implemented runtime and storage model.

## Phase 3: PRD closure sync

### Final PRD status update

- [x] Implement: update `prds/168-adaptive-support-profile-and-intervention-learning.md` to mark the last success criterion complete and record Milestone 6 progress/validation.
- [x] Run: `uv run ruff check src/alfred/support_policy.py tests/test_support_policy.py && uv run pytest --no-cov -p no:cacheprovider tests/test_support_policy.py -v`

## Files to Modify

1. `src/alfred/support_policy.py` - render the compact realization rule in the runtime support contract
2. `tests/test_support_policy.py` - regression coverage for the natural-phrasing boundary
3. `templates/SYSTEM.md` - managed prompt alignment with the runtime contract and situation-first learning model
4. `docs/relational-support-model.md` - architecture wording aligned to learning situations and derived episodes
5. `prds/168-adaptive-support-profile-and-intervention-learning.md` - final Milestone 6 progress/status update
6. `prds/execution-plan-168-milestone6.md` - this execution record

## Commit Strategy

Keep the final slice atomic if committed later:
- `test(policy): keep support contract semantic not script-like`
- `docs(prompt): align support learning model and phrasing boundary`
- `docs(prd): close milestone 6`
