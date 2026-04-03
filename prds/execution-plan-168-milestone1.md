# Execution Plan: PRD #168 - Milestone 1: Define the Relational and Support Registries

## Overview
This phase establishes the typed, versioned contract for Alfred's support-profile layer before any persistence or runtime policy resolution is added. The goal is to define the registry families, allowed values, defaults, and scope rules in one place so later milestones can store, resolve, and adapt values without inventing semantics ad hoc. Milestone 1 stops at contract validation: it should define one uniform scope object shape, the official global-scope representation, and the fixed v1 context taxonomy without trying to infer context from user messages yet.

## Current Repo Constraints
- `src/alfred/memory/support_memory.py` already defines typed support-memory records as dataclasses with explicit `to_record()` / `from_record()` helpers. Milestone 1 should match that style with frozen dataclasses and `__post_init__` validation so the support-profile contract fits the existing memory layer.
- `src/alfred/storage/sqlite.py` is already the single persistence boundary. Milestone 1 should stop short of schema changes and focus on the validation contract so storage work lands once the model shape is stable.
- PRD #168 now explicitly requires one uniform scope object shape and the v1 global-scope representation `{"type": "global", "id": "user"}`. The plan should not introduce nullable or alternate encodings that would create later storage drift.
- `docs/relational-support-model.md` already names the production relational and support dimensions and the fixed v1 interaction taxonomy. Milestone 1 must align with that vocabulary rather than accepting arbitrary context IDs.
- Public memory exports flow through `src/alfred/memory/__init__.py`. New support-profile types should be exported there rather than forcing deep imports from future callers.
- PRD #169 will depend on these registry and scoped-value contracts. Failing fast on invalid dimensions, invalid values, invalid context IDs, and invalid scopes now is safer than trying to correct bad records after persistence and adaptation logic exist.

## Success Signal
- Alfred has one versioned registry contract that defines both relational and support dimensions, their allowed values, defaults, and valid scopes.
- All scopes use one uniform object shape, and global scope uses the official v1 representation `{"type": "global", "id": "user"}`.
- Invalid dimensions, values, scope shapes, and context IDs fail fast at construction time.
- Valid scoped support-profile records can be created against the registry contract without touching SQLite yet.
- Milestone 1 proves contract validation only; it does not infer contexts from user messages or conversation state.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/test_support_profile.py` and `uv run mypy --strict src/`
- **Targeted tests for this phase:** `uv run pytest tests/test_support_profile.py -v`

---

## Phase 1: Milestone 1 - Define the relational and support registries

### Scope contract

- [x] Test: `test_support_profile_scope_accepts_only_global_context_and_arc_targets()` - verify the scoped-value contract accepts only the three PRD scopes, uses `{"type": "global", "id": "user"}` for global scope, accepts only the fixed v1 context IDs, and rejects malformed or unknown scope targets.
- [x] Implement: add a frozen `SupportProfileScope` dataclass with `__post_init__` validation in a new `src/alfred/memory/support_profile.py` module, keeping the scope contract independent from SQLite storage and stopping short of any runtime context inference.
- [x] Run: `uv run pytest tests/test_support_profile.py::test_support_profile_scope_accepts_only_global_context_and_arc_targets -v`

### Versioned registry catalog

- [x] Test: `test_registry_catalog_exposes_versioned_relational_and_support_families()` - verify Alfred exposes one versioned catalog with separate relational and support registry families rather than ad hoc freeform dimensions.
- [x] Implement: add the top-level registry catalog models and constants for schema version, registry kind, and dimension-family lookup.
- [x] Run: `uv run pytest tests/test_support_profile.py::test_registry_catalog_exposes_versioned_relational_and_support_families -v`

### Relational registry definitions

- [x] Test: `test_relational_registry_rejects_unknown_dimensions_and_invalid_values()` - verify documented relational dimensions such as `warmth` and `candor` have explicit allowed values, defaults, and scope rules while unknown dimensions or values are rejected.
- [x] Implement: define the relational registry entries and validation logic for the PRD #168 relational dimension set.
- [x] Run: `uv run pytest tests/test_support_profile.py::test_relational_registry_rejects_unknown_dimensions_and_invalid_values -v`

### Support registry definitions

- [x] Test: `test_support_registry_rejects_unknown_dimensions_and_invalid_values()` - verify documented support dimensions such as `option_bandwidth` and `recommendation_forcefulness` have explicit allowed values, defaults, and scope rules while unknown dimensions or values are rejected.
- [x] Implement: define the support registry entries and validation logic for the PRD #168 support dimension set.
- [x] Run: `uv run pytest tests/test_support_profile.py::test_support_registry_rejects_unknown_dimensions_and_invalid_values -v`

### Scoped support-profile value contract

- [x] Test: `test_support_profile_value_accepts_valid_scoped_records_and_rejects_cross_registry_mismatches()` - verify a scoped support-profile value record only accepts valid registry/dimension/value combinations and fails fast on cross-registry or out-of-scope misuse.
- [x] Implement: add the typed support-profile value record with registry-backed validation for scope, dimension, allowed value, status, source, confidence, and evidence refs.
- [x] Run: `uv run pytest tests/test_support_profile.py::test_support_profile_value_accepts_valid_scoped_records_and_rejects_cross_registry_mismatches -v`

---

## Files to Modify

1. `src/alfred/memory/support_profile.py` - new support-profile registry models, scope contract, and typed value validation
2. `src/alfred/memory/__init__.py` - re-export support-profile types for later storage and runtime callers
3. `tests/test_support_profile.py` - contract tests for scope validation, registry families, dimension definitions, and scoped value acceptance

## Commit Strategy

Each completed test → implement → run block should become one atomic commit:
- `feat(memory): add support profile scope contract`
- `feat(memory): add versioned support profile catalog`
- `feat(memory): define relational registry values`
- `feat(memory): define support registry values`
- `feat(memory): validate scoped support profile records`

Current next task priority: land the scope contract first, because the global-scope representation, fixed context taxonomy, and frozen-dataclass validation rules constrain every later registry and storage record.
