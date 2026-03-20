# Execution Plan: PRD #137 - Phase 1: Foundation

## Overview
Replace WrappedInput and custom focus management with native PyPiTUI Input and focus stack.

## Phase 1: Foundation - Replace Core Components

### Input Component Replacement

- [ ] **Test**: `test_input_placeholder_shows()` — Input displays placeholder text
- [ ] **Test**: `test_input_submit_callback()` — Input.on_submit fires on Enter
- [ ] **Test**: `test_input_max_length_enforced()` — Input respects max_length
- [ ] **Test**: `test_input_backspace_works()` — Backspace removes characters
- [ ] **Implement**: Replace `WrappedInput` with `from pypitui import Input`
- [ ] **Run**: `uv run pytest tests/pypitui/test_input.py -v`

### Focus Management Migration

- [ ] **Test**: `test_push_focus_on_start()` — Input focused on TUI start
- [ ] **Test**: `test_pop_focus_restores_previous()` — Focus restored after popup
- [ ] **Test**: `test_focus_lifecycle_callbacks()` — on_focus/on_blur called
- [ ] **Implement**: Replace `self.tui.set_focus()` with `self.tui.push_focus()`
- [ ] **Run**: `uv run pytest tests/pypitui/test_focus.py -v`

### Container Migration

- [ ] **Test**: `test_container_adds_children()` — Container.add_child() works
- [ ] **Test**: `test_container_layout_vertical()` — Children stack vertically
- [ ] **Implement**: Use `from pypitui import Container` instead of custom
- [ ] **Run**: `uv run pytest tests/pypitui/test_container.py -v`

### Delete wrapped_input.py

- [ ] **Verify**: No imports of `wrapped_input` remain
- [ ] **Delete**: `src/alfred/interfaces/pypitui/wrapped_input.py`
- [ ] **Run**: `uv run pytest tests/` — All tests pass
- [ ] **Commit**: `git commit -m "refactor(pypitui): replace WrappedInput with native Input"`

## Files Modified

1. `src/alfred/interfaces/pypitui/tui.py` — Use native Input, Container, focus

## Files Deleted

1. `src/alfred/interfaces/pypitui/wrapped_input.py` (412 lines)

## Progress

**Phase 1 Status**: 0/14 tasks complete

**Estimated**: 4 hours

**Dependencies**: PyPiTUI >= 1.0.0

## Success Criteria

- Input field works identically to before
- Focus management uses native push/pop
- Container uses native implementation
- 412 lines deleted
- All tests pass
