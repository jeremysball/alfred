# Execution Plan: PRD #183 - Milestone 4B (slice): Runtime resolves learned values from the v2 value ledger

## Overview
This slice begins the **runtime cutover** work by making the reply-time support-policy resolver prefer **v2 value-ledger entries** (case-derived learning) when loading learned support/relational values.

We keep the change narrow by wiring the v2 ledger into an existing public seam:
- `SQLiteStore.resolve_support_profile_value(...)`

This avoids touching TUI surfaces and keeps the current support-policy contract stable.

## Success Signal (observable)
Given stored learning:
- a v2 `SupportValueLedgerEntry` with status `active_auto` or `confirmed` for a `(registry, dimension, scope)`

When runtime resolves learned values:
- `SQLiteStore.resolve_support_profile_value(...)` returns an effective value matching the v2 ledger entry
- v1 `support_profile_values` are still used as fallback when there is no active v2 entry

## Repo Constraints
- The support-policy runtime currently calls `SupportPolicyStore.resolve_support_profile_value(...)` for each dimension.
- That protocol returns a **v1** `SupportProfileValue`.
- v2 ledger entries live in `support_value_ledger_entries` and can contain multiple values per dimension (contradictions) but should have at most one active entry.

## Design Decisions (this slice)
- Only v2 statuses `active_auto` and `confirmed` are eligible to be returned to runtime.
- v2 entries are adapted to a synthetic v1 `SupportProfileValue`:
  - `status`: `confirmed`
  - `source`: `auto_adapted`
  - `evidence_refs`: `(last_case_id,)` when present
  - timestamps + confidence: copied from the v2 entry
- Precedence is:
  1. scope specificity: `arc` → `context` → `global`
  2. within each scope: v2 active entry → v1 stored profile value

## Validation Workflow
Python
```bash
uv run ruff check src/ tests/storage/test_support_profile_storage.py
uv run mypy --strict src/
uv run pytest tests/storage/test_support_profile_storage.py -v
```

## Tasks
- [x] **Test-first:** add a storage test asserting that `resolve_support_profile_value()` prefers a v2 active value-ledger entry over a v1 profile value for the same `(registry, dimension, scope)`.
- [x] **Implement:** update `SQLiteStore.resolve_support_profile_value()` to consult `support_value_ledger_entries` (active statuses only) before falling back to `support_profile_values`.
- [x] **Run:** targeted ruff + mypy + pytest for the touched storage surface.

## Commit Strategy
- `feat(prd-183): runtime resolves values from v2 value ledger`
