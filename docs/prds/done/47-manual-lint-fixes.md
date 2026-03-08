# PRD: Manual Lint Fixes

## Overview

**Issue**: #47  
**Status**: Complete  
**Priority**: Medium  
**Created**: 2026-02-18
**Completed**: 2026-02-18

23 linting violations require manual fixes. These are non-trivial issues that ruff cannot auto-fix and require developer attention.

---

## Problem Statement

### Remaining Issues After Auto-Fix

| Code | Count | Description | Severity |
|------|-------|-------------|----------|
| E501 | 14 | Line too long (>100 chars) | Medium |
| B904 | 2 | Raise without from inside except | High |
| B905 | 2 | zip() without explicit strict | Medium |
| F841 | 2 | Unused variable | Low |
| F821 | 1 | Undefined name `json` | **Critical** |
| SIM103 | 1 | Needless bool | Low |

---

## Issue Details & Fixes

### F821 - Undefined Name (Critical)

**Location**: `src/llm.py:196`

```python
# Line 196 - json is not imported
data = json.loads(chunk)
```

**Fix**: Add `import json` at top of file

---

### B904 - Raise Without From Inside Except (High)

**Location**: `src/llm.py:83, 132`

```python
# Before (loses original traceback)
try:
    ...
except SomeError as e:
    raise NewError("message")  # ❌ Loses cause

# After (preserves traceback)
try:
    ...
except SomeError as e:
    raise NewError("message") from e  # ✅ Preserves cause
```

---

### E501 - Line Too Long (14 occurrences)

**Files**: `src/__main__.py`, `src/alfred.py`, `src/memory.py`, `src/search.py`, `src/llm.py`

**Example**:
```python
# Before (116 chars)
logger.info(f"Processing message from {user_id}: {message[:100]}...")

# After (multi-line)
logger.info(
    f"Processing message from {user_id}: {message[:100]}..."
)
```

**Strategy**:
- Break long strings with parentheses
- Use implicit continuation inside brackets
- Extract complex expressions to variables

---

### B905 - zip() Without Explicit Strict (Medium)

**Location**: `src/embeddings.py:142`, `src/memory.py:79`

```python
# Before
for a, b in zip(list1, list2):  # ❌ Unequal lengths silently truncated

# After  
for a, b in zip(list1, list2, strict=True):  # ✅ Raises on unequal lengths
```

**Decision needed**: Should these zips allow unequal lengths? If yes, add `# noqa: B905`.

---

### F841 - Unused Variable (Low)

**Location**: TBD (2 occurrences)

**Fix**: Either use the variable or remove the assignment.

---

### SIM103 - Needless Bool

**Location**: `src/embeddings.py:31`

```python
# Before
if condition:
    return True
else:
    return False

# After
return condition
```

---

## Milestones

| # | Milestone | Definition of Done |
|---|-----------|-------------------|
| 1 | Fix F821 undefined name | `import json` added, no NameError |
| 2 | Fix B904 raise-from | Both locations use `from err` |
| 3 | Fix E501 line length | All lines ≤100 chars, readable breaks |
| 4 | Fix B905 strict zip | Decision made, strict added or noqa |
| 5 | Fix F841 and SIM103 | Unused vars removed, needless bool fixed |
| 6 | CI Zero Errors | `ruff check src/` returns zero errors |

---

## Success Criteria

- `ruff check src/` returns zero errors
- `mypy src/` still passes (no type regressions)
- Test suite passes (219 tests)
- No functional changes to behavior
- Code remains readable after line breaks

---

## Dependencies

- Issue #46 (Auto-Fix Ruff) - should complete first

---

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| B905 strict=True or noqa? | TBD during implementation | - |
| Line break style | Use parentheses, not backslashes | - |

---

## Notes

- These are the final lint fixes before clean CI
- Requires careful manual review
- Consider running tests after each file is fixed

---

## Completion Evidence

**Completed in commit**: `2db9bdb chore(todo): complete tasks #45, #46, #47 - type safety and linting`

All 23 manual fixes applied:
- E501 (14): Long lines broken with parentheses
- B904 (2): `raise ... from err` pattern applied
- B905 (2): `zip(..., strict=True)` added
- F841 (2): Unused variables removed
- F821 (1): Missing `import json` added
- SIM103 (1): Needless bool simplified

**Verification**: `ruff check src/` passes with zero errors.
