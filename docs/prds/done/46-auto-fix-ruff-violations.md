# PRD: Auto-Fix Ruff Violations

## Overview

**Issue**: #46  
**Status**: Complete  
**Priority**: Medium  
**Created**: 2026-02-18
**Completed**: 2026-02-18

172 ruff linting violations can be auto-fixed. This PRD runs `ruff check --fix` to clean up whitespace, unused imports, import sorting, and modernization issues.

---

## Problem Statement

### Current State

ruff reports 225 total errors, with 172 auto-fixable:

| Code | Count | Fixable | Description |
|------|-------|---------|-------------|
| W293 | 168 | ✅ | Blank line contains whitespace |
| F401 | 12 | ✅ | Unused imports |
| UP045 | 10 | ✅ | Use `X \| None` instead of `Optional[X]` |
| I001 | 4 | ✅ | Unsorted imports |
| UP015 | 5 | ✅ | Unnecessary mode argument |
| UP035 | 2 | ✅ | Deprecated import |
| UP041 | 1 | ✅ | timeout-error-alias |
| W292 | 1 | ✅ | Missing newline at end of file |

### Why This Matters

- **Code consistency**: Uniform style across codebase
- **Clean diffs**: No whitespace noise in future PRs
- **Modern Python**: Uses latest Python 3.12 features
- **Import hygiene**: Removes dead imports, sorts imports

---

## Solution Overview

Run ruff auto-fix and verify:
```bash
uv run ruff check src/ --fix
```

Then manually review changes to ensure:
- No functional changes introduced
- Imports still resolve correctly
- Tests still pass

---

## Affected Rules Detail

### W293 - Blank Line Whitespace (168 occurrences)
Remove trailing whitespace on blank lines. Most common issue.

**Files affected**: 18+ files including `agent.py`, `alfred.py`, `llm.py`, `tools/*.py`

### F401 - Unused Imports (12 occurrences)
Remove unused imports like:
- `typing.Optional` (use `X | None` instead)
- `typing.Callable` (import from `collections.abc`)
- `src.tools.base.Tool` (imported but unused in agent.py)
- `src.llm.ChatResponse` (imported but unused in alfred.py)
- `asyncio` in cli.py

### UP045 - Non-PEP604 Annotation (10 occurrences)
Convert `Optional[X]` to `X | None`:
- `src/agent.py:40, 170`
- `src/llm.py:176, 184, 263, 370`

### I001 - Unsorted Imports (4 occurrences)
Reorder imports in:
- `src/llm.py:377`
- `src/memory.py:3`
- `src/tools/__init__.py:92`

### UP015 - Redundant Open Modes (5 occurrences)
Remove `"r"` from `open()` calls (it's the default):
- `src/memory.py:103, 115, 339`

### UP035 - Deprecated Import (2 occurrences)
Import from `collections.abc` instead of `typing`:
- `src/memory.py:6` - `AsyncIterator`
- `src/tools/base.py:6` - `Callable`

---

## Milestones

| # | Milestone | Definition of Done |
|---|-----------|-------------------|
| 1 | Run ruff --fix | Command executes successfully |
| 2 | Review W293 fixes | All whitespace cleaned, no functional changes |
| 3 | Review F401 fixes | Unused imports removed, no import errors |
| 4 | Review UP*/I001 fixes | Modern syntax applied, imports sorted |
| 5 | CI Zero Errors | `ruff check src/` returns only non-auto-fixable errors |

---

## Success Criteria

- `ruff check src/` reports only 23 non-auto-fixable errors (down from 225)
- All 172 auto-fixable errors resolved
- Test suite passes (219 tests)
- No functional changes to code behavior
- Git diff reviewed and approved

---

## Dependencies

- None - can run independently

---

## Notes

- Run this after #44 and #45 to avoid merge conflicts
- Commit with clear message: `style: auto-fix ruff violations`
- Review the diff before committing to ensure no surprises

---

## Completion Evidence

**Completed in commits**:
- `45ee345 style: fix all ruff linting errors`
- `e8bb724 style: format code with ruff`
- `2db9bdb chore(todo): complete tasks #45, #46, #47 - type safety and linting`

All 172 auto-fixable errors resolved:
- W293 (168): Blank line whitespace removed
- F401 (12): Unused imports removed
- UP045 (10): `Optional[X]` → `X | None`
- I001 (4): Import sorting
- UP015/UP035/UP041/W292: Modernization fixes

**Verification**: `ruff check src/` passes with only non-auto-fixable errors remaining (handled in #47).
