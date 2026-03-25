# Execution Plan: PRD #147 - Milestone 5: Surface /context Summary

## Overview
Add a self-model display to the `/context` command so users can inspect Alfred's internal runtime state.

---

## Milestone 5: Surface a compact `/context` summary

### Component: Add self-model to context display data

- [x] **Test**: `test_get_context_display_includes_self_model()` - verify self-model appears in context data
- [x] **Implement**: Add self-model extraction to `get_context_display()` in `context_display.py`
- [x] **Run**: `uv run pytest tests/test_context_display.py::test_get_context_display_includes_self_model -v`

### Component: Display self-model in TUI

- [x] **Implement**: Add "ALFRED SELF-MODEL" section to `ShowContextCommand` display
- [x] **Verify**: Display shows identity, runtime state, capabilities, context pressure
- [x] **Run**: Manual verification via TUI `/context` command

### Component: Fix existing tests

- [x] **Fix**: Update existing test to include `build_self_model` method on fake Alfred
- [x] **Run**: `uv run pytest tests/test_context_display.py -v`

---

## Files Modified

1. `src/alfred/context_display.py` — Added self-model section to return data
2. `src/alfred/interfaces/pypitui/commands/show_context.py` — Added display formatting
3. `tests/test_context_display.py` — Added test and fixed existing test

---

## Exit Criteria for Milestone 5

- `/context` command displays Alfred's self-model section
- Shows identity, interface, mode, capabilities, and context pressure
- Format is compact and readable
- All tests pass
- Ready for Milestone 6: Safety and regression tests
