# PRD #130: Code Quality Cleanup

## Overview

Systematic cleanup of code quality issues identified by radon, vulture, and mypy. This PRD addresses high cyclomatic complexity, dead code, and type safety issues.

## Current State

| Tool | Issues | Severity |
|------|--------|----------|
| **Radon** | 4 functions with grade D+ complexity | 🔴 High |
| **Vulture** | 0 issues | ✅ Complete |
| **MyPy** | 30 type errors | 🔴 High |

## Goals

1. **Reduce complexity** - Refactor functions with grade D+ complexity (24+)
2. **Eliminate dead code** - Remove/fix 4 unused variables
3. **Fix type errors** - Resolve 30 mypy strict mode errors

## Out of Scope

- Refactoring grade C functions (complexity 11-19) - these are acceptable
- Major architectural changes - focus on incremental improvements
- Adding new features - this is cleanup only

## Todo List (TDD)

### Phase 1: Dead Code (Quick Wins) ✅

- [x] Test: Verify unused variables exist and are safe to remove
- [x] Implement: Remove `bg` variable from `cli/main.py:112`
- [x] Implement: Remove `max_tokens` variable from `context.py:276`
- [x] Implement: Prefix unused `frame` params with `_` in `daemon.py`

### Phase 2: High Complexity Functions (Grade D+)

#### SocketServer._dispatch_message ✅

- [x] Test: Extract handler lookup logic
- [x] Implement: Create `_get_handler()` method
- [x] Test: Extract request handler lookup
- [x] Implement: Create `_get_request_handler()` method
- [x] Test: Extract response sending
- [x] Implement: Create `_send_response()` method
- [x] Verify: Complexity reduced from 30 (grade D) to 7 (grade B)

#### AlfredTUI._input_listener (Complexity 29)

- [ ] Test: Extract key handler dispatch
- [ ] Implement: Create `_dispatch_key_handler()` method
- [ ] Test: Extract command processing
- [ ] Implement: Create `_process_command()` method
- [ ] Verify: Complexity reduced to grade C or below

#### Agent.run_stream (Complexity 28)

- [ ] Test: Extract tool execution flow
- [ ] Implement: Create `_execute_tool_with_events()` method
- [ ] Test: Extract response handling
- [ ] Implement: Create `_handle_agent_response()` method
- [ ] Verify: Complexity reduced to grade C or below

#### config_update (Complexity 24)

- [ ] Test: Extract config validation
- [ ] Implement: Create `_validate_config_changes()` function
- [ ] Test: Extract config application
- [ ] Implement: Create `_apply_config_changes()` function
- [ ] Verify: Complexity reduced to grade C or below

#### KimiProvider.stream_chat_with_tools (Complexity 41)

- [ ] Test: Extract stream initialization
- [ ] Implement: Create `_init_tool_stream()` method
- [ ] Test: Extract chunk processing
- [ ] Implement: Create `_process_stream_chunk()` method
- [ ] Test: Extract tool call accumulation
- [ ] Implement: Create `_accumulate_tool_calls()` method
- [ ] Verify: Complexity reduced significantly

### Phase 3: Critical MyPy Errors

#### MemoryStore.search Signature

- [ ] Test: Verify SQLiteMemoryStore.search accepts query string
- [ ] Implement: Update base class signature or create adapter
- [ ] Verify: No more override error

#### SocketServer Response Types

- [ ] Test: Verify response type narrowing works
- [ ] Implement: Add Union return type or TypedDict
- [ ] Verify: No more assignment errors

#### Factory Type Issues

- [ ] Test: Verify SessionManager initialization types
- [ ] Implement: Fix Config vs Path type confusion
- [ ] Verify: factories.py and core.py pass mypy

#### SocketServer Async Handlers

- [ ] Test: Verify async handler type compatibility
- [ ] Implement: Update SocketServer to accept async handlers
- [ ] Verify: cli/main.py handler types pass

### Phase 4: Medium MyPy Errors

#### wrapped_input.py Private Access

- [ ] Test: Verify cursor position access works
- [ ] Implement: Use public API or add type: ignore with comment
- [ ] Verify: No more attr-defined errors

#### LLM Provider Return Types

- [ ] Test: Verify generic return type inference
- [ ] Implement: Add explicit casts or TypeVars
- [ ] Verify: llm.py passes mypy

#### BGE Provider Return Types

- [ ] Test: Verify embedding return types
- [ ] Implement: Add explicit list[float] casts
- [ ] Verify: bge_provider.py passes mypy

### Phase 5: Low Priority MyPy Errors

- [ ] Fix protocol.py asdict incompatibility
- [ ] Fix Alfred.memory_store attribute access
- [ ] Fix cron_runner.py unused coroutine warning
- [ ] Fix EmbeddingProvider/LLMProvider abstract class issues

## Progress Summary

### Completed ✅

**Phase 1 - Dead Code (100% complete):**
- Removed deprecated `bg` parameter from `daemon_start()` in `cli/main.py`
- Removed unused `max_tokens` parameter from `_format_tool_calls()` in `context.py`
- Prefixed unused `frame` params with `_` in signal handlers in `daemon.py`
- **Result:** Vulture now reports 0 issues

**Phase 2 - SocketServer Complexity (1 of 5 functions refactored):**
- Extracted `_get_handler()` for simple event message routing
- Extracted `_get_request_handler()` for request/response message routing
- Extracted `_send_response()` for response serialization
- Simplified `_dispatch_message()` using early returns instead of nested elifs
- **Result:** Complexity reduced from 30 (grade D) to 7 (grade B)
- **Tests:** All 8 socket server tests pass

### Remaining Work

**Phase 2 - High Complexity Functions (4 remaining):**
- `AlfredTUI._input_listener` (complexity 29)
- `Agent.run_stream` (complexity 28)
- `config_update` (complexity 24)
- `KimiProvider.stream_chat_with_tools` (complexity 41)

**Phase 3-5 - MyPy Errors (30 errors across 12 files):**
- MemoryStore.search signature override error
- SocketServer response type issues
- Factory type issues (Config vs Path confusion)
- Private attribute access in wrapped_input.py
- Generic return type issues in llm.py and bge_provider.py

## Success Criteria

| Metric | Before | Target |
|--------|--------|--------|
| Radon grade D+ | 5 functions | 0 functions |
| Radon grade F | 1 function | 0 functions |
| Vulture issues | 4 | 0 |
| MyPy errors | 30 | **0** (zero tolerance) |
| Test coverage | 64% | ≥64% (maintain) |

## Implementation Notes

1. **Commit after each task** - Small, atomic commits
2. **Run tests after every change** - Ensure no regressions
3. **Run radon/vulture/mypy after phase** - Verify progress
4. **Update this todo** - Mark tasks complete as you go

## Rollback Plan

If issues arise:
1. Revert specific commit (atomic changes allow this)
2. Document blocking issue
3. Skip to next task
4. Return later if time permits
