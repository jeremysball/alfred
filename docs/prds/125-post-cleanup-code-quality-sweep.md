# PRD #125: Post-Cleanup Code Quality Sweep

**Status**: 🟡 Ready for Implementation  
**Priority**: Medium  
**Created**: March 12, 2026  
**GitHub Issue**: #125

---

## Problem Statement

After the completion of PRD #122 (major codebase cleanup removing ~4,650 lines of dead code), residual code quality issues remain:

| Category | Count | Severity |
|----------|-------|----------|
| Ruff style violations | 224 | Low |
| Unused imports (tests) | 17 | Low |
| Dead code items (vulture 60%+) | ~150 | Medium |
| Unused variables (100% confidence) | 4 | Medium |

These issues:
- Clutter the codebase with unnecessary code
- Slow down linting and type checking
- Create false positives in code analysis
- Reduce maintainability

---

## Goals

1. **Eliminate all auto-fixable style issues** via `ruff --fix`
2. **Remove unused imports** from test files
3. **Remove 100% confidence dead code** (unused variables)
4. **Maintain full test coverage** - all 775+ tests must pass
5. **Preserve all active functionality** - zero behavioral changes

## Non-Goals

- No refactoring of active logic
- No removal of low-confidence dead code (< 80%)
- No changes to public APIs
- No behavioral changes

---

## Success Criteria

- [ ] `uv run ruff check src/ tests/` passes with zero errors
- [ ] `uv run ruff check src/ tests/ --select=F401` passes (no unused imports)
- [ ] 100% confidence dead code items removed (4 items)
- [ ] All 775+ tests passing
- [ ] Import check passes: `from alfred.alfred import Alfred`
- [ ] No coverage regression

---

## Current State Analysis

### Ruff Violations (224 total)

**By category:**
| Code | Description | Count |
|------|-------------|-------|
| W293 | Blank line contains whitespace | ~30 |
| W291 | Trailing whitespace | ~5 |
| E501 | Line too long | ~10 |
| SIM117 | Use single `with` statement | ~3 |
| I001 | Import block un-sorted | ~2 |
| F401 | Unused imports | 17 |

**Primary files affected:**
- `tests/tools/test_session_summarizer_sqlite.py` (20+ whitespace issues)

### Unused Imports (17 errors in test files)

| File | Unused Import |
|------|--------------|
| `tests/conftest.py` | `pathlib.Path` |
| `tests/cron/test_parser.py` | `timedelta`, `ZoneInfo`, `pytest` |
| `tests/cron/test_socket_api_behavior.py` | `json`, `tempfile`, `Path` |
| `tests/embeddings/test_provider.py` | `Path` |
| `tests/test_completion_performance.py` | `time`, `MagicMock` |
| `tests/test_container.py` | `SessionManager` |
| `tests/test_cron_tools_behavioral.py` | `Path` |
| `tests/test_job_linter.py` | `pytest`, `JobLinterError` |
| `tests/test_socket_server_handlers.py` | `json`, `datetime` |
| `tests/tools/test_cron_tools_socket.py` | `patch` |

### 100% Confidence Dead Code (4 items)

| File | Line | Issue | Action |
|------|------|-------|--------|
| `src/alfred/cli/main.py:112` | unused variable `bg` | Remove |
| `src/alfred/context.py:276` | unused variable `max_tokens` | Remove |
| `src/alfred/cron/daemon.py:188` | unused variable `frame` | Remove |
| `src/alfred/cron/daemon.py:196` | unused variable `frame` | Remove |

### 80%+ Confidence Dead Code (Priority: Lower)

**Cron job_linter.py:**
- `found_notify_call`, `found_subprocess_notify` attributes set but never read

**Config:**
- `memory_ttl_days`, `memory_warning_threshold` (may be referenced by templates)

---

## Implementation Plan

### Milestone 1: Automated Style Fixes
**Goal**: Fix all auto-fixable ruff violations

**Commands:**
```bash
uv run ruff check tests/ --select=W --fix
uv run ruff check src/ tests/ --select=E,I --fix
```

**Expected Impact**: ~200 issues resolved automatically

**Validation:**
- [ ] Remaining ruff violations < 30
- [ ] All tests pass

---

### Milestone 2: Remove Unused Imports
**Goal**: Eliminate 17 unused imports from test files

**Command:**
```bash
uv run ruff check tests/ --select=F401 --fix
```

**Files to verify:**
- [ ] `tests/conftest.py`
- [ ] `tests/cron/test_parser.py`
- [ ] `tests/cron/test_socket_api_behavior.py`
- [ ] `tests/embeddings/test_provider.py`
- [ ] `tests/test_completion_performance.py`
- [ ] `tests/test_container.py`
- [ ] `tests/test_cron_tools_behavioral.py`
- [ ] `tests/test_job_linter.py`
- [ ] `tests/test_socket_server_handlers.py`
- [ ] `tests/tools/test_cron_tools_socket.py`

**Validation:**
- [ ] `uv run ruff check tests/ --select=F401` passes
- [ ] All tests pass

---

### Milestone 3: Remove 100% Confidence Dead Code
**Goal**: Remove 4 unused variables with 100% confidence

**Changes:**

1. **src/alfred/cli/main.py:112**
   ```python
   # Remove unused 'bg' variable
   # Current: bg = background
   # Action: Remove line or use _ = background
   ```

2. **src/alfred/context.py:276**
   ```python
   # Remove unused 'max_tokens' variable
   # Verify not used in commented code or debugging
   ```

3. **src/alfred/cron/daemon.py:188,196**
   ```python
   # Remove unused 'frame' variables in exception handlers
   # These appear to be in 'for frame in...' loops where frame is unused
   ```

**Validation:**
- [ ] `vulture src/ --min-confidence=100` reports 0 issues
- [ ] All tests pass
- [ ] Import check passes

---

### Milestone 4: Final Verification
**Goal**: Ensure complete cleanup with zero regressions

**Final Checks:**
```bash
# 1. Full ruff check
uv run ruff check src/ tests/

# 2. Import check
uv run python -c "from alfred.alfred import Alfred"

# 3. Full test suite
uv run pytest tests/ -q

# 4. Coverage check (baseline: 63%)
uv run pytest tests/ --cov=src/alfred --cov-report=term-missing
```

**Validation:**
- [ ] Ruff: 0 errors
- [ ] Imports: Working
- [ ] Tests: 775+ passing
- [ ] Coverage: ≥ 63% (no regression)

---

## Exclusions (DO NOT REMOVE)

The following should be preserved:

1. **Low-confidence dead code (< 80%)** - May have side effects or be used by reflection
2. **TUI component attributes** - May be part of pypitui Component protocol
3. **Pydantic model_config** - Required by Pydantic even if appears unused
4. **Abstract methods** - Required by interface definitions
5. **Test fixtures** - May be used by conftest.py even if appears unused locally

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Auto-fix breaks code | Low | Medium | Run tests after each milestone |
| Unused import actually used | Low | High | Verify with grep before removing |
| Dead code has side effects | Low | Medium | 100% confidence only for explicit removal |
| Coverage drops | Low | Low | Monitor coverage report |

---

## Rollback Plan

1. Create backup branch before starting: `git branch backup/pre-cleanup-125`
2. Each milestone is independent and reversible
3. If issues: `git revert <commit>`
4. Full rollback: `git reset --hard backup/pre-cleanup-125`

---

## Progress Tracking

| Milestone | Status | Commit |
|-----------|--------|--------|
| 1: Automated Style Fixes | ⬜ Not Started | TBD |
| 2: Remove Unused Imports | ⬜ Not Started | TBD |
| 3: Remove 100% Dead Code | ⬜ Not Started | TBD |
| 4: Final Verification | ⬜ Not Started | TBD |

---

## Expected Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Ruff errors | 224 | 0 | -224 (100%) |
| Unused imports | 17 | 0 | -17 (100%) |
| 100% dead code | 4 | 0 | -4 (100%) |
| Tests passing | 775 | 775 | 0 (stable) |
| Coverage | 63% | ≥63% | No regression |

---

## Related PRDs

- PRD #122: Codebase Cleanup - Dead Code Removal (completed)
- PRD #109: Great Consolidation (completed)

---

*Note: This PRD focuses on residual cleanup after PRD #122. It does not repeat the scope of #122 but addresses the remaining code quality issues identified through automated analysis.*