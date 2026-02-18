# PRD: Fix Tool Class Type Safety

## Overview

**Issue**: #44  
**Status**: Complete  
**Priority**: High  
**Created**: 2026-02-18  
**Completed**: 2026-02-18

Tool subclasses have incompatible method signatures with the base `Tool` class. This violates the Liskov Substitution Principle and causes mypy errors that indicate potential runtime bugs.

---

## Problem Statement

### Current State

The base `Tool` class defines:
```python
def execute(self, **kwargs: Any) -> str | dict[str, Any]: ...
def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]: ...
```

But subclasses implement concrete parameter lists:
```python
def execute(self, path: str, content: str) -> dict[Any, Any]  # ❌ Wrong!
def execute_stream(self, command: str, timeout: int | None = ...) -> str  # ❌ Wrong!
```

### Impact

- **8 tools affected**: `write`, `read`, `edit`, `bash`, `remember`, `forget`, `search_memories`, `update_memory`
- **Type safety broken**: Subclasses cannot be used where base class is expected
- **CI failures**: mypy strict mode reports override errors
- **Potential runtime bugs**: Invalid method signatures may cause unexpected behavior

---

## Solution Overview

Refactor all tool `execute()` and `execute_stream()` methods to:
1. Accept `**kwargs: Any` matching base class signature
2. Extract and validate parameters internally
3. Return correct types (`str | dict[str, Any]` for sync, `AsyncIterator[str]` for async)

---

## Affected Files

| File | Issue |
|------|-------|
| `src/tools/write.py:17` | Signature mismatch |
| `src/tools/read.py:17` | Signature mismatch |
| `src/tools/edit.py:14` | Signature mismatch |
| `src/tools/bash.py:19` | Signature mismatch |
| `src/tools/remember.py:30` | Signature mismatch |
| `src/tools/remember.py:50` | Signature mismatch (execute_stream) |
| `src/tools/forget.py:22` | Signature mismatch |
| `src/tools/forget.py:40` | Signature mismatch (execute_stream) |
| `src/tools/search_memories.py:22` | Signature mismatch |
| `src/tools/search_memories.py:40` | Signature mismatch (execute_stream) |
| `src/tools/update_memory.py:22` | Signature mismatch |
| `src/tools/update_memory.py:44` | Signature mismatch (execute_stream) |

---

## Implementation Pattern

### Before (❌ Wrong)
```python
def execute(self, path: str, content: str) -> dict[Any, Any]:
    with open(path, "w") as f:
        f.write(content)
    return {"status": "success"}
```

### After (✅ Correct)
```python
def execute(self, **kwargs: Any) -> str | dict[str, Any]:
    path = kwargs.get("path")
    content = kwargs.get("content")
    if not path or not content:
        return {"status": "error", "message": "Missing required parameters"}
    with open(path, "w") as f:
        f.write(content)
    return {"status": "success"}
```

---

## Milestones

| # | Milestone | Definition of Done |
|---|-----------|-------------------|
| [x] | 1 | Refactor write.py and read.py | Both tools use `**kwargs`, mypy passes |
| [x] | 2 | Refactor edit.py and bash.py | Both tools use `**kwargs`, mypy passes |
| [x] | 3 | Refactor memory tools (remember, forget) | Both tools use `**kwargs`, mypy passes |
| [x] | 4 | Refactor search/update tools | Both tools use `**kwargs`, mypy passes |
| [x] | 5 | CI Zero Errors | `mypy src/` returns no override errors |

---

## Success Criteria

- `mypy src/` reports zero `override` errors
- All tools can be instantiated and called polymorphically
- Test suite passes (219 tests)
- No functional changes to tool behavior

---

## Dependencies

- None - this is foundational work

---

## Notes

- Changes are purely structural; tool behavior remains identical
- Tool schemas (for LLM) remain unchanged
- Parameter validation should be added where missing
