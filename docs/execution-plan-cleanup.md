# Execution Plan: Dead Code Cleanup

**Goal**: Remove dead code, cruft, and poor quality tests to improve maintainability.

**Estimated Impact**: ~120+ issues, ~3000+ lines removed

---

## Phase 1: Safe Removals (No Dependencies)

### 1.1 Remove Empty Files
**Files to delete:**
- `tests/__init__.py` (0 lines)
- `src/alfred/cli/__init__.py` (1 line)
- `tests/pypitui/__init__.py` (1 line)
- `tests/embeddings/__init__.py` (1 line)
- `src/alfred/interfaces/__init__.py` (1 line)
- `src/alfred/utils/__init__.py` (3 lines)
- `src/alfred/storage/__init__.py` (3 lines)
- `tests/e2e/__init__.py` (4 lines)

**Verification:**
```bash
uv run pytest tests/ -x --tb=short
```

---

### 1.2 Remove FAISS Config Remnants
**File:** `src/alfred/config.py`

**Remove lines 59-61:**
```python
faiss_index_type: str = "flat"
faiss_ivf_threshold: int = 10000
faiss_backup_jsonl: bool = True
```

**Commit:** `chore(config): remove FAISS remnants`

---

### 1.3 Remove Unused Type Definitions
**File:** `src/alfred/type_defs.py`

**Remove function `ensure_json_object()` (lines 12+)**

**Commit:** `chore(types): remove unused ensure_json_object`

---

## Phase 2: Remove Unused Cron/Notifier Code

### 2.1 Remove Natural Language Cron Parser
**File:** `src/alfred/cron/nlp_parser.py`

**Action:** Delete entire file (400+ lines of unused NLP code)

**Verification:**
```bash
uv run python -c "from alfred.cron import parser; print('OK')"
```

**Commit:** `chore(cron): remove unused NaturalLanguageCronParser`

---

### 2.2 Remove Unused Notifier Classes
**File:** `src/alfred/cron/notifier.py`

**Remove:**
- `NotifierError` class (lines 17-19)
- `CLINotifier` class (lines 69-100)
- `TelegramNotifier` class (lines 193-238)
- `set_buffer()` method (lines 101-107)
- `set_toast_manager()` method (lines 109-116)
- `flush_buffer()` method (lines 171-191)

**Commit:** `chore(cron): remove unused notifier classes`

---

### 2.3 Remove Other Unused Cron Methods
**File:** `src/alfred/cron/observability.py`
- Remove `log_warning()` method (line 109)

**File:** `src/alfred/cron/parser.py`
- Remove `get_next_run()` function (line 38)

**File:** `src/alfred/cron/store.py`
- Remove `get_job_history()` method (line 118)

**Commit:** `chore(cron): remove unused utility methods`

---

## Phase 3: Remove Unused Memory/Storage Code

### 3.1 Remove Unused MemoryStore Methods
**File:** `src/alfred/memory/sqlite_store.py`

**Remove:**
- `prune_expired_memories()` (lines 205-210)
- `delete_entries()` (lines 254-280)
- `check_memory_threshold()` (lines 282-297)

**Commit:** `chore(memory): remove unused store methods`

---

### 3.2 Remove Unused SQLiteStore Methods
**File:** `src/alfred/storage/sqlite.py`

**Remove:**
- `delete_session()` (lines 399-415)
- `find_sessions_needing_summary()` (lines 1083-1109)

**Commit:** `chore(storage): remove unused SQLite methods`

---

## Phase 4: Remove Interface Dead Code

### 4.1 Remove Notification Buffer
**File:** `src/alfred/interfaces/notification_buffer.py`

**Action:** Delete entire file

**Commit:** `chore(interface): remove unused NotificationBuffer`

---

### 4.2 Remove SessionContextBuilder
**File:** `src/alfred/session_context.py`

**Action:** Delete entire file

**Commit:** `chore(session): remove unused SessionContextBuilder`

---

### 4.3 Remove StatusRenderer
**File:** `src/alfred/interfaces/status.py`

**Action:** Delete entire file

**Commit:** `chore(interface): remove unused StatusRenderer`

---

## Phase 5: Remove Tool Dead Code

### 5.1 Remove Unused Tool Methods
**File:** `src/alfred/tools/__init__.py`
- Remove `clear_registry()` (line 73)
- Remove `get_tool_schemas()` (line 80)

**File:** `src/alfred/tools/approve_job.py`
- Remove `validate_identifier()` (line 23)

**File:** `src/alfred/tools/reject_job.py`
- Remove `validate_identifier()` (line 23)

**File:** `src/alfred/tools/schedule_job.py`
- Remove `validate_name()` (line 45)
- Remove `validate_description()` (line 53)

**Commit:** `chore(tools): remove unused validation methods`

---

## Phase 6: Remove Placeholder Dead Code

### 6.1 Remove Placeholder Utilities
**File:** `src/alfred/placeholders.py`

**Remove:**
- `CircularReferenceError` class (line 19)
- `resolve_file_includes()` function (line 291)
- `resolve_colors()` function (line 310)

**Commit:** `chore(placeholders): remove unused utilities`

---

## Phase 7: Remove Obsolete Test Files

### 7.1 Remove Tests for Removed Components
**Files to delete:**
- `tests/test_cas_store.py` (~150 lines) - Tests CAS store (removed in PRD #109)
- `tests/test_memory.py` (~200 lines) - Tests old JSONL memory store
- `tests/test_memory_crud.py` (~100 lines) - Tests obsolete memory CRUD
- `tests/test_remember_tool.py` (~150 lines) - Tests old tool implementation
- `tests/test_unified_memory_system.py` (~180 lines) - Tests superseded by PRD #102
- `tests/tools/test_memory_integration.py` (~120 lines) - Obsolete integration tests

**Commit:** `test: remove tests for deleted components`

---

### 7.2 Remove Tests Using Old Singleton Pattern
**Files to delete:**
- `tests/test_session_cli.py` (~200 lines) - Uses old SessionManager singleton
- `tests/tools/test_schedule_job.py` (~180 lines) - Empty test bodies
- `tests/tools/test_forget.py` (~150 lines) - Empty test bodies
- `tests/tools/test_schedule_job_integration.py` (~200 lines) - Obsolete integration

**Commit:** `test: remove obsolete test files using old patterns`

---

### 7.3 Remove Skipped Tests
**File:** `tests/pypitui/test_notifier_toast.py`
- Remove `test_cli_notifier_with_buffer()` (line 40)

**File:** `tests/tools/test_update_memory.py`
- Remove test at line 74 with `pytest.skip`

**Commit:** `test: remove skipped tests`

---

## Phase 8: Final Cleanup

### 8.1 Remove Unused LLM Methods
**File:** `src/alfred/llm.py`
- Remove `retry_with_backoff()` decorator (line 117)

**Commit:** `chore(llm): remove unused retry decorator`

---

### 8.2 Clean Up Unused Variables
**File:** `src/alfred/context.py`
- Remove unused `max_tokens` variable (line 276)

**Commit:** `chore(context): remove unused variable`

---

## Verification Steps

After each phase, run:

```bash
# Lint check
uv run ruff check src/ tests/

# Type check
uv run basedpyright src/

# Tests
uv run pytest tests/ -x --tb=short

# Import check
uv run python -c "from alfred.alfred import Alfred; print('Imports OK')"
```

---

## Rollback Plan

If issues arise:
1. Each commit is atomic - revert individual commits
2. Keep a backup branch before starting: `git branch backup/pre-cleanup`
3. Run full test suite before each commit

---

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| Total Files | ~180 | ~150 |
| Lines of Code | ~15,000 | ~11,000 |
| Unused Classes | 15+ | 0 |
| Obsolete Test Files | 10 | 0 |
| Skipped Tests | 6 | 0 |
| Test Coverage | Baseline | +5% |

## Files to be Deleted (Complete List)

### Source Files (~1,500 lines)
1. `src/alfred/cron/nlp_parser.py` (400 lines)
2. `src/alfred/interfaces/notification_buffer.py` (70 lines)
3. `src/alfred/session_context.py` (50 lines)
4. `src/alfred/interfaces/status.py` (50 lines)
5. `src/alfred/type_defs.py` (partial, ~20 lines)
6. `src/alfred/__init__.py` (keep version only, ~3 lines)
7. Empty `__init__.py` files (8 files, ~15 lines)

### Test Files (~2,000 lines)
1. `tests/test_cas_store.py` (~150 lines)
2. `tests/test_memory.py` (~200 lines)
3. `tests/test_memory_crud.py` (~100 lines)
4. `tests/test_remember_tool.py` (~150 lines)
5. `tests/test_unified_memory_system.py` (~180 lines)
6. `tests/tools/test_memory_integration.py` (~120 lines)
7. `tests/test_session_cli.py` (~200 lines)
8. `tests/tools/test_schedule_job.py` (~180 lines)
9. `tests/tools/test_forget.py` (~150 lines)
10. `tests/tools/test_schedule_job_integration.py` (~200 lines)

### **Total Lines Removed: ~3,500**

---

**Start Date**: [Fill in]
**Estimated Duration**: 1-2 days
**Owner**: [Fill in]
