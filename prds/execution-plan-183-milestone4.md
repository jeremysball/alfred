# Execution Plan: PRD #183 - Milestone 4A: Deterministic case finalization from persisted attempt bundles

## Overview
Start Milestone 4 at the new public seam that already exists: persisted `SupportAttempt` plus appended `OutcomeObservation` rows. This slice adds one deterministic case-finalization contract that scores a stored attempt bundle into a durable `LearningCase`, without depending on new conversational producers or semantic extraction.

## Current Repo Constraints
- `src/alfred/support_policy.py` still applies the older `LearningSituation` bounded-adaptation path before generation; Milestone 4 must move toward `SupportAttempt` → `OutcomeObservation` → `LearningCase` without trying to replace the whole runtime in one jump.
- `src/alfred/storage/sqlite.py` can already persist and load `SupportAttempt`, `OutcomeObservation`, and `LearningCase`, but there is no public helper that synthesizes a case from stored attempt evidence.
- Milestone 3A now appends deterministic `work_state_transition` observations from public operational storage seams, so there is real persisted evidence to score even before conversational extraction lands.
- Conversational and semantic observation producers remain out of scope for this slice; the scoring contract must work with whatever observations already exist.
- The repo still has unrelated in-flight changes, so this slice should stay bounded to the support-learning model, SQLite store, tests, and milestone plan.

## Success Signal
- Given one stored `SupportAttempt` and its persisted observations, Alfred can derive one deterministic `LearningCase` with explicit scope, aggregate signals, evidence counts, channel scores, and promotion eligibility.
- The SQLite store exposes one public seam that finalizes and persists that case for a specific attempt.
- Attempts without any observations do not fabricate a finalized case.
- Contradictory or neutral-only evidence remains inspectable through `LearningCase`, but only sufficiently positive, low-contradiction cases become promotion-eligible.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/test_support_learning.py tests/storage/test_support_learning_storage.py` and `uv run mypy --strict src/`
- **Targeted tests:** run the smallest pytest command listed under each task

---

## Phase 1: Derive deterministic cases from persisted observations

### Add a pure attempt-plus-observation case derivation contract

- [x] Test: add `test_derive_learning_case_scores_conversational_and_operational_evidence()` in `tests/test_support_learning.py` — verify scope selection, aggregate signals, evidence counts, scores, and promotion eligibility for a positive mixed-source case.
- [x] Test: add `test_derive_learning_case_marks_neutral_only_evidence_as_insufficient()` in `tests/test_support_learning.py` — verify neutral-only evidence finalizes as inspectable but not promotion-eligible.
- [x] Implement: add the minimal deterministic case-derivation helpers in `src/alfred/memory/support_learning.py` for scoring observations into one `LearningCase`.
- [x] Run: `uv run pytest tests/test_support_learning.py::test_derive_learning_case_scores_conversational_and_operational_evidence tests/test_support_learning.py::test_derive_learning_case_marks_neutral_only_evidence_as_insufficient -v`

### Persist finalized cases from the SQLite public seam

- [x] Test: add `test_sqlite_store_finalize_support_learning_case_persists_scored_case_from_attempt_observations()` in `tests/storage/test_support_learning_storage.py` — verify the store finalizes, persists, and returns the deterministic case for a stored attempt bundle.
- [x] Test: add `test_sqlite_store_finalize_support_learning_case_skips_attempts_without_observations()` in `tests/storage/test_support_learning_storage.py` — verify missing or observation-free attempts do not fabricate finalized cases.
- [x] Implement: extend `src/alfred/storage/sqlite.py` with the minimal attempt/observation loading and public case-finalization helper needed to persist the derived case.
- [x] Run: `uv run pytest tests/storage/test_support_learning_storage.py::test_sqlite_store_finalize_support_learning_case_persists_scored_case_from_attempt_observations tests/storage/test_support_learning_storage.py::test_sqlite_store_finalize_support_learning_case_skips_attempts_without_observations -v`

---

## Final phase verification

- [x] Run: `uv run ruff check src/ tests/test_support_learning.py tests/storage/test_support_learning_storage.py`
- [x] Run: `uv run mypy --strict src/`
- [x] Run: `uv run pytest tests/test_support_learning.py tests/storage/test_support_learning_storage.py -v`

## Files to Modify

1. `prds/execution-plan-183-milestone4.md` - milestone plan and validation record
2. `src/alfred/memory/support_learning.py` - deterministic learning-case derivation helpers
3. `src/alfred/storage/sqlite.py` - public case-finalization seam for one attempt bundle
4. `tests/test_support_learning.py` - pure model scoring coverage for deterministic case derivation
5. `tests/storage/test_support_learning_storage.py` - SQLite case-finalization regression coverage

## Commit Strategy

Keep this slice atomic:
- `feat(memory): finalize v2 learning cases from observations`
