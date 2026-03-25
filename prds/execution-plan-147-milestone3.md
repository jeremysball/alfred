# Execution Plan: PRD #147 - Milestone 3: Build Runtime Self-State Assembly

## Overview
Integrate the self-model builder into the Alfred class so it can create runtime snapshots from live state. This milestone connects the contract from Milestone 1 to the actual Alfred instance.

---

## Milestone 3: Build runtime self-state assembly

### Component: Alfred class integration

- [x] **Test**: `test_alfred_class_has_build_self_model_method()` - verify Alfred class has build_self_model method with correct signature
- [x] **Implement**: add `build_self_model()` method to Alfred class that calls `build_runtime_self_model(self)`
- [x] **Run**: `uv run pytest tests/test_self_model.py::test_alfred_class_has_build_self_model_method -v`

### Component: Method behavior verification

- [x] **Test**: `test_fake_alfred_with_build_self_model_method()` - verify the pattern works with a fake Alfred that mimics the real interface
- [x] **Implement**: ensure imports work correctly and method returns RuntimeSelfModel
- [x] **Run**: `uv run pytest tests/test_self_model.py::test_fake_alfred_with_build_self_model_method -v`

---

## Files Modified

1. `src/alfred/alfred.py` — added `build_self_model()` method and imports
2. `tests/test_self_model.py` — added integration tests for Alfred class method

---

## Exit Criteria for Milestone 3

- Alfred class has a working `build_self_model()` method
- Method returns a `RuntimeSelfModel` populated from current runtime state
- Tests verify the integration without requiring full Alfred instantiation
- Ready for Milestone 4: Inject self-model into context assembly
