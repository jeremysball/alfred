# PRD: Cron Job Linter and Socket API Decoupling

**GitHub Issue**: [#120](https://github.com/jeremysball/alfred/issues/120)  
**Status**: 🟡 In Progress  
**Priority**: High  
**Created**: 2026-03-07  

---

## Problem

Alfred's TUI freezes intermittently, causing complete UI unresponsiveness. Investigation revealed that user-submitted cron jobs can contain blocking code (e.g., `subprocess.run`, `time.sleep`, `requests.get`) that blocks the asyncio event loop when executed in-process.

Additionally, the current architecture tightly couples Alfred with the cron subsystem:
- Alfred initializes `CronScheduler` directly
- Tools like `list_jobs` and `approve_job` access the database directly
- This makes it impossible to run cron as a standalone daemon
- No validation of job code before submission

## Solution

### 1. AST-Based Job Linter
Add static analysis to detect common "foot guns" in user-submitted cron job code:
- Blocking subprocess calls (`subprocess.run`, `subprocess.call`, etc.)
- Blocking I/O (`open()`, `input()`)
- Synchronous HTTP requests (`requests.get`, `requests.post`)
- Blocking sleep (`time.sleep` instead of `asyncio.sleep`)
- Wrong notify usage (calling external `notify` binary instead of injected function)

### 2. Socket API for Decoupling
Decouple Alfred from cron by having tools query a daemon via Unix domain socket:
- Tools become API clients, not database clients
- Fresh data from daemon preferred over cached DB state
- Allows running cron as standalone daemon
- Better separation of concerns

## Success Criteria

- [ ] Jobs with blocking calls are rejected at submission time with clear error messages
- [ ] Cron tools (`list_jobs`, `approve_job`, etc.) use socket API instead of direct DB access
- [ ] Alfred no longer initializes `CronScheduler` (daemon-only)
- [ ] TUI no longer freezes due to blocking cron jobs
- [ ] Socket API provides fresh job status data

---

## Milestones

### Milestone 1: Job Linter Implementation ✅
**Status**: Complete  
**Commit**: `6bc1a30`

- [x] Create `src/alfred/cron/job_linter.py` with AST-based analysis
- [x] Detect blocking calls (subprocess, time.sleep, requests, etc.)
- [x] Detect wrong notify() usage patterns
- [x] Integrate linter into `submit_user_job()` and `approve_job()`
- [x] Add 24 comprehensive tests in `tests/test_job_linter.py`
- [x] Create `src/alfred/cron/README.md` documenting architecture

**Files Created/Modified**:
- `src/alfred/cron/job_linter.py` (new)
- `src/alfred/cron/scheduler.py` (modified)
- `tests/test_job_linter.py` (new)
- `src/alfred/cron/README.md` (new)

### Milestone 2: Session Tool Calls Bug Fix ✅
**Status**: Complete  
**Commit**: `6bc1a30`

- [x] Fix `_create_session_from_data()` to convert dict tool_calls to `ToolCallRecord` objects
- [x] Fix `_persist_messages()` to serialize `ToolCallRecord` properly
- [x] Fix `_spawn_persist_task()` to pass `session.messages` instead of single message

**Files Modified**:
- `src/alfred/session.py`
- `src/alfred/alfred.py`

### Milestone 3: Socket Protocol Expansion 🔄
**Status**: In Progress

- [x] Add `QUERY_JOBS`, `SUBMIT_JOB`, `APPROVE_JOB`, `REJECT_JOB` message types
- [x] Add request/response dataclasses in `socket_protocol.py`
- [x] Add client methods in `socket_client.py`
- [ ] Implement server dispatch handlers in `socket_server.py`
- [ ] Test query/response flow end-to-end

**Files Modified**:
- `src/alfred/cron/socket_protocol.py`
- `src/alfred/cron/socket_client.py`
- `src/alfred/cron/socket_server.py` (partial)

### Milestone 4: Tool Migration to Socket API ⏳
**Status**: Not Started

- [ ] Update `list_jobs` tool to use `SocketClient.query_jobs()`
- [ ] Update `approve_job` tool to use `SocketClient.approve_job()`
- [ ] Update `schedule_job` tool to use `SocketClient.submit_job()`
- [ ] Update `reject_job` tool to use `SocketClient.reject_job()`
- [ ] Remove direct database access from tools

**Files to Modify**:
- `src/alfred/tools/list_jobs.py`
- `src/alfred/tools/approve_job.py`
- `src/alfred/tools/schedule_job.py`
- `src/alfred/tools/reject_job.py`

### Milestone 5: Alfred Decoupling ⏳
**Status**: Not Started

- [ ] Remove `CronScheduler` initialization from `Alfred.__init__()`
- [ ] Update Alfred to only start cron in daemon mode (`--daemon` flag)
- [ ] Ensure Alfred TUI doesn't depend on cron scheduler
- [ ] Update CLI to support daemon-only cron mode

**Files to Modify**:
- `src/alfred/alfred.py`
- `src/cli/main.py`

### Milestone 6: Testing & Validation ⏳
**Status**: Not Started

- [ ] Test linting catches all blocking patterns
- [ ] Test socket API handles concurrent requests
- [ ] Test tool migration doesn't break existing workflows
- [ ] Test daemon-only mode works independently
- [ ] Verify TUI stability under load

### Milestone 7: Documentation Updates ⏳
**Status**: Not Started

- [ ] Update main README with new cron architecture
- [ ] Document socket protocol for external integrations
- [ ] Add troubleshooting guide for job linting errors
- [ ] Update architecture diagrams

---

## Architecture

### Before (Tightly Coupled)
```
┌─────────────────┐
│   Alfred TUI    │◄──── User interaction
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌───────────────┐
│  CronScheduler  │────►│  SQLite DB    │
│  (in-process)   │     │               │
└────────┬────────┘     └───────────────┘
         │
         ▼
┌─────────────────┐
│  JobExecutor    │◄──── Jobs run in-process
│  (blocking!)    │      blocks event loop
└─────────────────┘
```

### After (Decoupled)
```
┌─────────────────┐
│   Alfred TUI    │◄──── User interaction
└────────┬────────┘
         │ Socket API
         ▼
┌─────────────────┐     ┌───────────────┐
│  Cron Daemon    │────►│  SQLite DB    │
│  (standalone)   │     │               │
└────────┬────────┘     └───────────────┘
         │
         ▼
┌─────────────────┐
│  JobExecutor    │◄──── Jobs run in isolated
│  (subprocess)   │      subprocess (non-blocking)
└─────────────────┘
```

### Socket Protocol

**Unix Domain Socket**: `~/.cache/alfred/notify.sock`  
**Format**: JSON + newline delimiter

**Message Types**:
- `QUERY_JOBS` / `QUERY_JOBS_RESPONSE` - Get job status
- `SUBMIT_JOB` / `SUBMIT_JOB_RESPONSE` - Submit new job
- `APPROVE_JOB` / `APPROVE_JOB_RESPONSE` - Approve pending job
- `REJECT_JOB` / `REJECT_JOB_RESPONSE` - Reject pending job
- `JOB_COMPLETED` / `JOB_FAILED` - Execution notifications

---

## Job Linter Details

### Detected Patterns

| Pattern | Severity | Suggestion |
|---------|----------|------------|
| `subprocess.run()` | Error | Use `asyncio.create_subprocess_exec()` |
| `subprocess.call()` | Error | Use `asyncio.create_subprocess_exec()` |
| `subprocess.check_output()` | Error | Use `asyncio.create_subprocess_exec()` with streams |
| `time.sleep()` | Error | Use `asyncio.sleep()` |
| `requests.get()` | Error | Use `httpx.AsyncClient` or `aiohttp` |
| `requests.post()` | Error | Use `httpx.AsyncClient` or `aiohttp` |
| `os.system()` | Error | Use `asyncio.create_subprocess_shell()` |
| `open()` | Error | Use `aiofiles` or `anyio.open_file()` |
| `input()` | Error | Not allowed in cron jobs |
| `subprocess.run(['notify', ...])` | Warning | Use injected `notify()` function instead |

### Example Lint Output

```python
code = """
import subprocess
def run():
    subprocess.run(['echo', 'hello'])
    time.sleep(5)
"""

errors = lint_job_code(code)
# [
#   JobLinterError(
#     message="Blocking call: subprocess.run",
#     line=4,
#     suggestion="Use asyncio subprocess: 'asyncio.create_subprocess_exec'..."
#   ),
#   JobLinterError(
#     message="Blocking call: time.sleep",
#     line=5,
#     suggestion="Use asyncio.sleep instead"
#   )
# ]
```

---

## Decisions & Notes

### Decision: AST vs Regex
**Choice**: Use Python's `ast` module instead of regex for parsing.

**Rationale**:
- AST understands scope (won't flag comments/strings)
- Can detect imports and track what's being called
- More maintainable than complex regex patterns
- Better error messages with line numbers

### Decision: Unix Domain Socket vs TCP
**Choice**: Continue using file-based socket at `~/.cache/alfred/notify.sock`

**Rationale**:
- Simpler security (filesystem permissions)
- No port conflicts
- Works well for single-machine deployment
- Easier to clean up (just delete the file)

### Decision: Fresh Data vs Cached
**Choice**: Socket API returns fresh data from daemon, not cached DB state

**Rationale**:
- Daemon is the source of truth
- Avoids stale data issues
- Simpler mental model for developers
- Allows daemon to add computed fields (e.g., "next run in")

### Decision: Edge Conversion Pattern
**Choice**: Convert dicts to objects at storage edge (loading), use proper classes everywhere inside

**Rationale**:
- Type safety throughout the codebase
- Consistent interface for business logic
- Easier refactoring with IDE support
- Catches errors at load time, not use time

---

## Related Issues

- **Freeze Root Cause**: Job "HN Good News" (ID: f6aeb893-75f1-4a70-9931-f47dbf09ff88) runs every 5 min, uses `subprocess.run(['notify', message])` which doesn't exist → `FileNotFoundError` + blocks event loop
- **Tool Calls Bug**: Session restoration was failing because `tool_calls` were dicts instead of `ToolCallRecord` objects

---

## Appendix

### A. Files Modified/Created

**New Files**:
- `src/alfred/cron/job_linter.py` - AST-based linting
- `tests/test_job_linter.py` - Linter tests
- `src/alfred/cron/README.md` - Architecture documentation

**Modified Files**:
- `src/alfred/cron/scheduler.py` - Integrated linter
- `src/alfred/cron/socket_protocol.py` - Added new message types
- `src/alfred/cron/socket_client.py` - Added API methods
- `src/alfred/cron/socket_server.py` - Partial implementation
- `src/alfred/session.py` - Fixed tool_calls conversion
- `src/alfred/alfred.py` - Fixed persist task

### B. Test Coverage

```
tests/test_job_linter.py:
- test_subprocess_run_detected
- test_subprocess_call_detected
- test_time_sleep_detected
- test_requests_get_detected
- test_requests_post_detected
- test_os_system_detected
- test_file_open_detected
- test_input_detected
- test_asyncio_sleep_allowed
- test_aiohttp_allowed
- test_subprocess_notify_detected
- test_correct_notify_usage_allowed
- test_missing_async_def_run
- test_missing_run_function
- test_empty_code
- test_syntax_error_handling
- test_complex_code_multiple_issues
- test_aliased_import_detection
- test_from_import_detection
- test_nested_function_calls
- test_no_false_positives_in_strings
- test_no_false_positives_in_comments
- test_valid_async_job_passes
- test_format_lint_errors
```

---

*Last Updated: 2026-03-07*
