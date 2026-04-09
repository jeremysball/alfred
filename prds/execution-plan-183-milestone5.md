# Execution Plan: PRD #183 - Milestone 5A: Case-based value ledger promotion from finalized cases

## Overview
Start Milestone 5 at the narrowest promotion seam that now exists: finalized `LearningCase` records plus their source `SupportAttempt` bundles. This slice promotes support and relational values into the v2 value ledger with explicit `shadow` and `active_auto` statuses, while deferring patterns, demotion, runtime rewiring, and cross-scope generalization.

## Current Repo Constraints
- `src/alfred/support_policy.py` still uses the older `LearningSituation` bounded-adaptation path before generation, so this slice must establish case-based ledger derivation without replacing runtime loading yet.
- `src/alfred/memory/support_learning.py` can now derive deterministic `LearningCase` records, but a case alone does not identify which values Alfred applied; Milestone 5A must join each finalized case back to its source `SupportAttempt`.
- `src/alfred/storage/sqlite.py` already persists `SupportValueLedgerEntry` and `SupportLedgerUpdateEvent`, but no public seam yet derives those rows from finalized case bundles.
- This slice should stay exact-scope only: `arc` and `context` scopes may promote, while `global`, cross-arc rollup, demotion, retirement, and pattern inference stay out of scope.
- The product decision for this slice is to persist below-threshold evidence as inspectable `shadow` rows rather than discarding it.
- The repo still has unrelated in-flight changes, so keep this work bounded to support-learning models, storage, tests, and PRD planning docs.

## Success Signal
- Given finalized case bundles in one exact scope, Alfred can derive deterministic `SupportValueLedgerEntry` rows for the values actually used in those attempts and persist them as `shadow` or `active_auto` based on repeated promotable evidence.
- Arc-scoped values promote after two supporting promotable cases, while context-scoped values require four.
- Conflicting same-scope values on the same dimension increase `contradiction_count` and block `active_auto` when support is not stronger than contradiction.
- The SQLite store exposes one public seam that applies case-based learning for a finalized case and writes the resulting value-ledger rows and update events transactionally.
- Missing, unfinalized, or non-promotable case bundles do not fabricate ledger rows or events.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/test_support_learning.py tests/storage/test_support_learning_storage.py` and `uv run mypy --strict src/`
- **Targeted tests:** run the smallest pytest command listed under each task

---

## Phase 1: Derive exact-scope value-ledger updates from finalized case bundles

### Persist inspectable shadow rows before promotion thresholds are met

- [x] Test: add `test_derive_value_ledger_updates_persists_shadow_rows_below_exact_scope_thresholds()` in `tests/test_support_learning.py` — verify one promotable arc-scoped support value and one promotable context-scoped relational value persist as `shadow` with evidence counts, confidence, and update events.
- [x] Implement: add the minimal finalized-case bundle type plus pure exact-scope value-ledger derivation in `src/alfred/memory/support_learning.py`.
- [x] Run: `uv run pytest tests/test_support_learning.py::test_derive_value_ledger_updates_persists_shadow_rows_below_exact_scope_thresholds -v`

### Promote repeated scoped values and count contradictions deterministically

- [x] Test: add `test_derive_value_ledger_updates_promotes_after_threshold_and_blocks_when_conflicts_win()` in `tests/test_support_learning.py` — verify a second supporting arc case promotes the same value to `active_auto`, while conflicting same-dimension evidence increases contradiction counts and blocks activation when support is not stronger.
- [x] Implement: extend the pure derivation logic with exact-scope thresholds, contradiction counting, and status transitions for existing value-ledger rows.
- [x] Run: `uv run pytest tests/test_support_learning.py::test_derive_value_ledger_updates_promotes_after_threshold_and_blocks_when_conflicts_win -v`

### Apply finalized-case learning through the SQLite public seam

- [x] Test: add `test_sqlite_store_apply_support_case_learning_persists_shadow_then_active_auto_updates()` in `tests/storage/test_support_learning_storage.py` — verify applying learning for one finalized case writes `shadow` rows and events, then a second supporting finalized case upgrades the same scoped value to `active_auto`.
- [x] Implement: extend `src/alfred/storage/sqlite.py` with the minimal attempt/case bundle loading and transactional `apply_support_case_learning(case_id)` seam needed to persist derived value-ledger rows and update events.
- [x] Run: `uv run pytest tests/storage/test_support_learning_storage.py::test_sqlite_store_apply_support_case_learning_persists_shadow_then_active_auto_updates -v`

### Skip missing or non-applicable case bundles cleanly

- [x] Test: add `test_sqlite_store_apply_support_case_learning_skips_missing_or_non_promotable_cases()` in `tests/storage/test_support_learning_storage.py` — verify missing cases, unfinalized cases, and non-promotable finalized bundles do not fabricate ledger rows or events.
- [x] Implement: keep the new storage seam bounded so only finalized promotable case bundles with resolvable attempts write ledger updates.
- [x] Run: `uv run pytest tests/storage/test_support_learning_storage.py::test_sqlite_store_apply_support_case_learning_skips_missing_or_non_promotable_cases -v`

---

## Final phase verification

- [x] Run: `uv run ruff check src/ tests/test_support_learning.py tests/storage/test_support_learning_storage.py`
- [x] Run: `uv run mypy --strict src/`
- [x] Run: `uv run pytest tests/test_support_learning.py tests/storage/test_support_learning_storage.py -v`

## Files to Modify

1. `prds/execution-plan-183-milestone5.md` - milestone plan and validation record
2. `src/alfred/memory/support_learning.py` - pure finalized-case bundle derivation for v2 value-ledger updates
3. `src/alfred/storage/sqlite.py` - public transactional seam that applies case-based value learning
4. `tests/test_support_learning.py` - pure model coverage for thresholds, contradictions, and shadow persistence
5. `tests/storage/test_support_learning_storage.py` - SQLite regression coverage for case-based value-ledger writes

## Commit Strategy

Keep this slice atomic:
- `feat(memory): derive v2 value ledger updates from finalized cases`
