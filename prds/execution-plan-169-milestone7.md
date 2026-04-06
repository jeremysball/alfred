# Execution Plan: PRD #169 - Milestone 7 Docs and Prompt Sync

## Overview
Sync the shipped reflection behavior with the durable docs and managed prompt/template surfaces so Alfred's review, inspection, and correction model is described consistently.

## Current Repo Constraints
- Reflection behavior now lives in `src/alfred/support_reflection.py`, `src/alfred/alfred.py`, and the Web UI slash-command handlers. Docs must describe the shipped bounded surfaces rather than the earlier fully-planned state.
- Managed prompts should describe policy ownership, candidate-first identity/direction handling, and bounded reflective surfacing without leaking internal labels.
- Docs-only changes do not require code validation unless they change behavior claims or prompt semantics. This slice updates description and prompt wording only.

## Success Signal
- Architecture and memory docs describe learning situations, derived review cards, inspection/correction surfaces, and bounded reflective surfacing in terms that match the current runtime.
- Managed templates tell the model to keep reflection bounded, natural, and tentative where required.

## Validation Workflow
- **Workflow:** Docs / prompt sync only
- **Checks:** manual read-through of updated docs and templates for agreement with shipped runtime behavior

---

## Phase 1: Architecture and memory docs

- [x] Update `docs/ARCHITECTURE.md` to describe learning situations as the primary learning unit, episodes as derived synthesis, and inspection/correction as explicit reflection surfaces.
- [x] Update `docs/MEMORY.md` to describe typed learning situations, derived review cards, current correction flows, and the learning-situation promotion ladder.
- [x] Update `docs/relational-support-model.md` to align pattern kinds, derived review-card kinds, inspection/correction surfaces, and bounded surfacing rules with the current runtime.

## Phase 2: User-facing description and managed prompts

- [x] Update `docs/how-alfred-helps.md` to describe the bounded inspection, review, and correction surfaces now available.
- [x] Update `templates/SYSTEM.md` so reflection guidance stays compact, natural, and candidate-first for identity/direction themes.
- [x] Update `templates/prompts/boundaries.md` so reflective pattern surfacing remains bounded and tentative where required.
