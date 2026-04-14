# Execution Plan: PRD #183 - Milestone 4B.2 (Option A): Retire bounded adaptation (`LearningSituation`) in runtime

## Overview
Milestone 4B.2 (Option A) removes the **turn-centric bounded adaptation** path from the reply-time runtime.

This intentionally does **not** add any new semantic extraction or new promotion triggers.

## Success Signal (observable)
When `SupportPolicyRuntime.build_turn_contract()` is called with a `query_embedding`:
- it does **not** persist `LearningSituation`
- it does **not** write v1 support-profile update events/pattern candidates via bounded adaptation
- the runtime still resolves values deterministically via defaults + stored scoped values (now including v2 ledger-derived values via `resolve_support_profile_value`)

## Validation Workflow
Python
```bash
uv run ruff check src/ tests/test_support_policy.py
uv run mypy --strict src/
uv run pytest tests/test_support_policy.py -v
```

## Tasks
- [x] **Test-first:** update `tests/test_support_policy.py` to assert that the runtime no longer persists learning situations / bounded adaptation artifacts.
- [x] **Implement:** turn `SupportPolicyRuntime._maybe_apply_bounded_adaptation(...)` into a no-op and remove the post-adaptation second-pass resolve.
- [x] **Run:** targeted ruff + mypy + pytest.

## Commit Strategy
- `feat(prd-183): retire bounded adaptation runtime path`
