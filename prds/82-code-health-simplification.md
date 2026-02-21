# PRD: Code Health & Simplification

## Overview

**Issue**: #82
**Status**: Draft
**Priority**: Medium
**Created**: 2026-02-21
**Target**: ~1,170 line reduction

Systematic audit to remove dead code, eliminate duplication, simplify over-engineered abstractions, and improve overall code health.

---

## Problem Statement

The Alfred codebase has grown organically, accumulating:

- **Dead code**: Unused functions, placeholder methods, and orphaned logic
- **Duplication**: Identical or near-identical code in multiple locations
- **Over-engineering**: Complex abstractions that could be simpler
- **Boilerplate**: Repetitive patterns that could be consolidated

This increases maintenance burden, slows code review, and obscures the actual business logic.

---

## Solution Overview

A balanced cleanup effort targeting ~1,000 line reduction through:

1. **Dead Code Elimination** — Remove unused functions and placeholder methods
2. **Deduplication** — Consolidate identical code into shared utilities
3. **Simplification** — Reduce unnecessary abstractions
4. **Refactoring** — Apply consistent patterns to reduce boilerplate

---

## Scope

### In Scope

| Category | Target Lines | Files Affected | Risk Level |
|----------|--------------|----------------|------------|
| Dead code removal | ~90 | 1 | Low |
| Duplicate `__builtins__` consolidation | ~150 | 2 | Medium |
| Unused `_create_safe_globals` | ~70 | 1 | Low |
| Dual retry logic unification | ~50 | 1 | Medium |
| Tool `execute()` boilerplate | ~100 | 10 | Low |
| CLI async wrapper (decorator) | ~100 | 1 | Low |
| Observability simplification | ~480 | 1 | Low |
| Test deduplication | ~200 | 2 | Low |

**Total Target**: ~1,170 lines

### Out of Scope

- Functional changes to Alfred's behavior
- API changes
- New features
- Performance optimization (beyond code clarity)
- Major architectural restructuring

---

## Detailed Findings

### 1. Duplicate `__builtins__` Dictionary (High Impact)

**Files**: `src/cron/scheduler.py`, `src/cron/executor.py`
**Lines**: ~150 combined
**Risk**: Medium

Both files define identical 70+ entry `__builtins__` dictionaries for sandboxed job execution.

**Current State**:
```python
# scheduler.py (lines 325-370)
namespace = {
    "__builtins__": {
        "print": print,
        "len": len,
        # ... 70+ more entries
    }
}

# executor.py (lines 249-310)
def _create_safe_globals(self) -> dict[str, Any]:
    return {
        "__builtins__": {
            "print": print,
            "len": len,
            # ... same 70+ entries
        }
    }
```

**Recommendation**: Extract to shared `src/cron/sandbox.py` module.

---

### 2. Dead `store_get`/`store_set` Methods (Low Impact)

**File**: `src/cron/executor.py`
**Lines**: ~20
**Risk**: Low

`ExecutionContext.store_get()` and `store_set()` are TODO placeholders that return `None` and do nothing. They're exposed to jobs but non-functional.

**Current State**:
```python
def store_get(self, key: str) -> Any:
    """Get a value from the job's key-value store."""
    # TODO: Implement persistent KV store per job
    return None

def store_set(self, key: str, value: Any) -> None:
    """Set a value in the job's key-value store."""
    # TODO: Implement persistent KV store per job
    pass
```

**Recommendation**: Remove until actually needed, or implement.

---

### 3. Unused `_create_safe_globals` Method (Low Impact)

**File**: `src/cron/executor.py`
**Lines**: ~70
**Risk**: Low

`JobExecutor._create_safe_globals()` is defined but never called. The scheduler has its own implementation.

**Recommendation**: Delete the unused method.

---

### 4. Dual Retry Logic (Medium Impact)

**File**: `src/llm.py`
**Lines**: ~50
**Risk**: Medium

Two implementations of retry logic:
- `_retry_async()` — standalone async function
- `@retry_with_backoff` — decorator

Both do the same thing. The decorator can't be used in async generators, hence the duplication.

**Recommendation**: Keep both but extract shared logic to a common helper.

---

### 5. Tool `execute()` Boilerplate (Medium Impact)

**Files**: 10 tool files in `src/tools/`
**Lines**: ~100 combined
**Risk**: Low

Most tools implement:
```python
def execute(self, **kwargs: Any) -> str:
    return "Error: XTool must be called via execute_stream in async context"
```

This is required by the `Tool` base class but adds no value.

**Recommendation**: Make base `Tool.execute()` return this message, remove overrides.

---

### 6. CLI Async Wrapper Pattern (Medium Impact)

**File**: `src/cli/cron.py`
**Lines**: ~100
**Risk**: Medium

17 commands follow this pattern:
```python
@app.command("list")
def list_jobs(...) -> None:
    asyncio.run(_list_jobs_async(...))

async def _list_jobs_async(...) -> None:
    # actual implementation
```

**Recommendation**: Use a decorator or Typer's async support.

---

### 7. Observability Complexity (High Impact)

**File**: `src/cron/observability.py`
**Lines**: 559 → ~80 (save ~480)
**Risk**: Low

Current components:

| Component | Lines | Action | Reason |
|-----------|-------|--------|--------|
| Counter | ~30 | Delete | In-memory only, never exposed |
| Histogram | ~50 | Delete | In-memory only, never exposed |
| Gauge | ~40 | Delete | In-memory only, never exposed |
| CronMetrics | ~40 | Delete | Just groups the above |
| HealthChecker | ~60 | Delete | Duplicates scheduler tracking |
| AlertManager | ~70 | Delete | Alerts go nowhere useful |
| StructuredLogger | ~80 | **Keep** | Writes useful JSONL logs to `data/cron_logs.jsonl` |
| Observability | ~30 | Simplify | Just wrap StructuredLogger |

**Recommendation**: Keep `StructuredLogger`, delete everything else.

---

### 8. Test Duplication (Low Impact)

**Files**: Multiple test files
**Lines**: ~200
**Risk**: Low

Some test files test the same functionality at different levels:
- `test_forget.py` (290 lines)
- `test_forget_new.py` (610 lines)

Overlap exists between integration and unit tests.

**Recommendation**: Consolidate related tests, remove redundant cases.

---

## Milestones

| # | Milestone | Lines Removed | Risk | Est. Effort |
|---|-----------|---------------|------|-------------|
| M1 | Remove dead code (store_*, _create_safe_globals) | ~90 | Low | 1h |
| M2 | Consolidate tool execute() boilerplate | ~100 | Low | 1h |
| M3 | Unify retry logic in llm.py | ~50 | Medium | 1h |
| M4 | Extract shared sandbox builtins | ~150 | Medium | 2h |
| M5 | Add @async_command decorator for CLI | ~100 | Low | 1h |
| M6 | Simplify observability (keep StructuredLogger only) | ~480 | Low | 2h |
| M7 | Merge forget tool tests | ~200 | Low | 1h |

**Total**: ~1,170 lines, ~9 hours estimated effort

---

## Success Criteria

- [ ] Line count reduced by ~1,170 lines (8,433 → ~7,260)
- [ ] All tests passing after cleanup
- [ ] No functional regressions
- [ ] Code coverage maintained or improved
- [ ] Ruff and mypy pass with no new warnings
- [ ] StructuredLogger still writes to `data/cron_logs.jsonl`

---

## Implementation Order

Recommended sequence (safe to risky):

1. **M1** - Dead code removal (safest, immediate benefit)
2. **M2** - Tool boilerplate (safe, reduces duplication)
3. **M3** - Retry logic (low risk, improves maintainability)
4. **M4** - Sandbox builtins (medium risk, high impact)
5. **M5** - CLI async decorator (low risk, clean pattern)
6. **M6** - Observability simplification (low risk, high savings)
7. **M7** - Test merge (safe, verify coverage)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking sandbox behavior | Run all cron tests before/after M1 |
| Removing still-used code | Grep for all references before deletion |
| Test coverage drop | Run coverage report after each milestone |
| Observability needed later | Keep simplified version, archive full version |

---

## Notes

- This is a **balanced** cleanup — not aggressive, not conservative
- All changes should be reviewed via PR before merging
- Each milestone should be a separate commit for easy rollback
- If any milestone proves controversial, skip it and move on
