# PRD: Add Missing Type Annotations

## Overview

**Issue**: #45  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-18

Multiple functions across the codebase lack type annotations, causing mypy strict mode failures. This PRD adds complete type annotations to achieve full mypy compliance.

---

## Problem Statement

### Current State

mypy with strict mode reports missing type annotations:
- `no-untyped-def`: 12+ functions without type annotations
- `type-arg`: 5+ generic types without parameters (e.g., `dict` instead of `dict[str, Any]`)
- `var-annotated`: Variables need explicit type annotations

### Specific Issues

| File | Line | Issue |
|------|------|-------|
| `src/types.py:26` | `model_post_init` | Missing return type |
| `src/tools/remember.py:22` | `__init__` | Missing type annotation |
| `src/tools/remember.py:26` | `set_memory_store` | Missing type annotation |
| `src/tools/forget.py:14` | `__init__` | Missing type annotation |
| `src/tools/forget.py:18` | `set_memory_store` | Missing type annotation |
| `src/tools/search_memories.py:14` | `__init__` | Missing type annotation |
| `src/tools/search_memories.py:18` | `set_memory_store` | Missing type annotation |
| `src/tools/update_memory.py:14` | `__init__` | Missing type annotation |
| `src/tools/update_memory.py:18` | `set_memory_store` | Missing type annotation |
| `src/tools/__init__.py:86` | Function argument | Missing type annotation |
| `src/tools/bash.py:107` | `stdout_data` | Need type annotation |
| `src/tools/bash.py:108` | `stderr_data` | Need type annotation |
| `src/llm.py:20` | `dict` | Missing type parameters |
| `src/llm.py:29` | `dict` | Missing type parameters |
| `src/llm.py:30` | `dict` | Missing type parameters |
| `src/llm.py:55` | `_stream_chunk` | Missing annotations |
| `src/llm.py:114` | `__init__` | Missing type annotation |
| `src/llm.py:115` | `message` | Missing type annotation |
| `src/llm.py:176` | `dict` | Missing type parameters |
| `src/tools/write.py:21` | `dict` | Missing type parameters |
| `src/tools/edit.py:19` | `dict` | Missing type parameters |
| `src/tools/bash.py:23` | `dict` | Missing type parameters |

---

## Solution Overview

Add comprehensive type annotations:
1. Add return types to all methods (`-> None`, `-> str`, etc.)
2. Add type parameters to generics (`dict[str, Any]`)
3. Add type annotations to function parameters
4. Add type annotations to variables where inference fails

---

## Implementation Examples

### Function Return Types
```python
# Before
def model_post_init(self, __context):
    pass

# After  
def model_post_init(self, __context: Any) -> None:
    pass
```

### Generic Type Parameters
```python
# Before
def execute(self, **kwargs: Any) -> dict[Any, Any]:

# After
def execute(self, **kwargs: Any) -> dict[str, Any]:
```

### Variable Annotations
```python
# Before
stdout_data = []
stderr_data = []

# After
stdout_data: list[str] = []
stderr_data: list[str] = []
```

---

## Milestones

| # | Milestone | Definition of Done |
|---|-----------|-------------------|
| 1 | Annotate src/types.py | All functions have complete types |
| 2 | Annotate src/tools/ | All tool classes fully typed |
| 3 | Annotate src/llm.py | All functions have complete types |
| 4 | Annotate remaining src/ files | All other files fully typed |
| 5 | CI Zero Errors | `mypy src/` returns no type errors |

---

## Success Criteria

- `mypy src/` reports zero `no-untyped-def`, `type-arg`, or `var-annotated` errors
- All public functions have type annotations
- No `Any` used where more specific types are possible
- Test suite passes (219 tests)

---

## Dependencies

- Issue #44 (Tool Class Type Safety) - should be completed first or done together

---

## Notes

- Use `from __future__ import annotations` where needed for forward references
- Prefer `X | None` over `Optional[X]` (Python 3.10+ style)
- Import types from `collections.abc` for abstract types (Iterator, Callable, etc.)
