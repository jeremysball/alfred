# Skipped basedpyright Errors

This document lists the basedpyright errors that were intentionally skipped during the type fix pass.

## Files Skipped Per User Request

### 1. `src/memory/faiss_store.py`
**Reason:** Unimplemented feature (PRD #105 - FAISS memory store is not yet implemented)

**Errors (7):**
- Line 54: `Expected type arguments for generic class "dict"`
- Line 66: `Expected type arguments for generic class "dict"`
- Line 174: `Cannot access attribute "xb" for class "IndexIVFFlat"`
- Line 182: `Argument missing for parameter "x"`
- Line 183: `Argument missing for parameter "x"`
- Line 206: `Argument missing for parameter "x"`
- Line 244: `Arguments missing for parameters "k", "distances", "labels"`

### 2. `src/interfaces/cli.py`
**Reason:** Dead code scheduled for deletion

**Errors (3):**
- Line 192: `Cannot access attribute "notifier" for class "Alfred"`
- Line 193: `Cannot access attribute "notifier" for class "Alfred"`
- Line 194: `Cannot access attribute "notifier" for class "Alfred"`

**Note:** The `Alfred` class has no `notifier` attribute. This code block attempts to access `alfred.notifier` which doesn't exist.

## Structural Errors (Require Architectural Changes)

### Import Cycle Detection Errors (7 files)
**Reason:** Fixing import cycles requires refactoring module structure

**Files affected:**
1. `src/cron/__init__.py` - Cycle detected in import chain
2. `src/interfaces/pypitui/commands/__init__.py` - Cycle detected in import chain (4 instances)
3. `src/interfaces/pypitui/completion_addon.py` - Cycle detected in import chain
4. `src/session.py` - Cycle detected in import chain

## Pypitui Stubs Updated

The following attributes were added to pypitui type stubs to fix errors:

### `pypitui/components.pyi` - `Input` class
- Added `on_submit: Callable[[str], None] | None`
- Added `_cursor_pos: int`
- Added `set_cursor_pos(pos: int) -> None` method

### `pypitui/tui.pyi` - `Container` class
- Added `children: list[Component]`

### `pypitui/tui.pyi` - `TUI` class
- Added `terminal: Terminal`

## Hallucinated Attributes (Commented Out)

### `TUI.on_resize`
**Location:** `src/interfaces/pypitui/tui.py:56` (commented out)

**Issue:** The code attempted to set `self.tui.on_resize = self._on_resize`, but `TUI` class in pypitui has no `on_resize` attribute or callback mechanism. The `_check_resize` method in TUI handles resize internally but does not support external callbacks.

**Resolution:** Commented out the assignment. The `_on_resize` method in `AlfredTUI` exists but is never called because pypitui doesn't support resize callbacks.

## Summary

| Category | Count |
|----------|-------|
| FAISS (unimplemented) | 7 |
| CLI dead code | 3 |
| Import cycles | 7 |
| **Total Skipped** | **17** |

All other type errors have been fixed.
