# Execution Plan: PRD #147 - Milestone 1: Self-Model Contract

## Overview
Define Alfred’s runtime self-model as a small, internal-only contract. This phase establishes the shape of Alfred’s self-knowledge and the builder that captures live runtime facts. It intentionally stops before prompt plumbing, SOUL.md rewrites, or `/context` exposure.

---

## Milestone 1: Define the self-model contract

### Component: Runtime self-model schema

- [x] **Test**: `test_runtime_self_model_includes_identity_runtime_and_world_sections()` - verify the contract contains identity, runtime, world, capability, and visibility fields
- [x] **Implement**: add `src/alfred/self_model.py` with Pydantic models for the runtime snapshot and an explicit internal-only visibility flag
- [x] **Run**: `uv run pytest tests/test_self_model.py::test_runtime_self_model_includes_identity_runtime_and_world_sections -v`

### Component: Runtime snapshot builder

- [x] **Test**: `test_build_runtime_self_model_uses_current_alfred_state()` - verify a fake Alfred produces a snapshot with current interface, session, daemon, tools, and context-pressure facts
- [x] **Implement**: add a runtime snapshot builder and a small Alfred accessor that assembles the model from live state instead of hardcoded prose
- [x] **Run**: `uv run pytest tests/test_self_model.py::test_build_runtime_self_model_uses_current_alfred_state -v`

### Component: Fail-closed unknown state handling

- [x] **Test**: `test_runtime_self_model_omits_unknown_fields_instead_of_fabricating_them()` - verify missing runtime facts become unknown/omitted and never get invented
- [x] **Implement**: add defensive defaults and serialization rules so the model degrades cleanly when a subsystem is unavailable
- [x] **Run**: `uv run pytest tests/test_self_model.py::test_runtime_self_model_omits_unknown_fields_instead_of_fabricating_them -v`

---

## Files to Modify

1. `src/alfred/self_model.py` — new runtime self-model contract and snapshot builder
2. `src/alfred/alfred.py` — expose live runtime facts needed to build the snapshot
3. `tests/test_self_model.py` — new contract tests for schema, builder, and fallback behavior

## Commit Strategy

Each completed checkbox should be one atomic commit:
- `test(self-model): define runtime snapshot contract`
- `feat(self-model): add runtime snapshot builder`
- `test(self-model): verify unknown state fails closed`

## Exit Criteria for Milestone 1

- Alfred has a stable internal self-model contract
- Runtime facts come from live state rather than static prose
- Missing data fails closed instead of being hallucinated
- Milestone 2 can safely rewrite SOUL.md on top of the contract
