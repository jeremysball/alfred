# Execution Plan: PRD #120 Milestone 4 - Tool Migration to Socket API

## Current State

### ✅ Completed
- Socket protocol with all message types (`QueryJobsRequest/Response`, `SubmitJobRequest/Response`, `ApproveJobRequest/Response`, `RejectJobRequest/Response`)
- SocketClient with methods: `query_jobs()`, `submit_job()`, `approve_job()`, `reject_job()`
- SocketServer handles: `NotifyMessage`, `JobStartedMessage`, `JobCompletedMessage`, `JobFailedMessage`, `PingMessage`, `QueryJobsRequest`

### ⏳ Remaining for Milestone 4
- SocketServer needs handlers for: `ApproveJobRequest`, `SubmitJobRequest`, `RejectJobRequest`
- Tools need to use `SocketClient` instead of `CronScheduler`
- Tool registration needs to inject `SocketClient`

---

## Granular Execution Plan

### Phase 1: Update SocketServer with Job Management Handlers

#### 1.1 Add callback parameters to SocketServer
- [ ] Add `on_submit_job`, `on_approve_job`, `on_reject_job` callback parameters to `__init__`
- [ ] Store callbacks as instance attributes
- [ ] Update `_dispatch_message` to handle `SubmitJobRequest`, `ApproveJobRequest`, `RejectJobRequest`

**Files:**
- `src/alfred/cron/socket_server.py`

**Test:**
- [ ] Write test: `test_socket_server_handles_submit_job_request()`
- [ ] Write test: `test_socket_server_handles_approve_job_request()`
- [ ] Write test: `test_socket_server_handles_reject_job_request()`

#### 1.2 Add handler implementations in main.py
- [ ] Create `_handle_submit_job()` function that uses scheduler
- [ ] Create `_handle_approve_job()` function that uses scheduler
- [ ] Create `_handle_reject_job()` function that uses scheduler
- [ ] Pass handlers to `SocketServer` constructor

**Files:**
- `src/alfred/cli/main.py`

---

### Phase 2: Update Tools to Use SocketClient

#### 2.1 Update ListJobsTool
- [ ] Change `__init__` to accept `socket_client: SocketClient` instead of `scheduler: CronScheduler`
- [ ] Update `execute_stream()` to use `await self.socket_client.query_jobs()`
- [ ] Convert `JobInfo` dataclass responses to dict format for tool output
- [ ] Remove direct store access

**Files:**
- `src/alfred/tools/list_jobs.py`

**Test:**
- [ ] Write test: `test_list_jobs_uses_socket_client()`
- [ ] Write test: `test_list_jobs_formats_output_correctly()`

#### 2.2 Update ApproveJobTool
- [ ] Change `__init__` to accept `socket_client: SocketClient`
- [ ] Update `execute_stream()` to use `await self.socket_client.approve_job()`
- [ ] Remove direct store access and `_find_job()` method (handled by daemon)
- [ ] Update response handling

**Files:**
- `src/alfred/tools/approve_job.py`

**Test:**
- [ ] Write test: `test_approve_job_uses_socket_client()`
- [ ] Write test: `test_approve_job_handles_failure()`

#### 2.3 Update ScheduleJobTool
- [ ] Change `__init__` to accept `socket_client: SocketClient`
- [ ] Update `execute_stream()` to use `await self.socket_client.submit_job()`
- [ ] Remove direct scheduler access
- [ ] Update response handling

**Files:**
- `src/alfred/tools/schedule_job.py`

**Test:**
- [ ] Write test: `test_schedule_job_uses_socket_client()`
- [ ] Write test: `test_schedule_job_handles_validation()`

#### 2.4 Update RejectJobTool
- [ ] Change `__init__` to accept `socket_client: SocketClient`
- [ ] Update `execute_stream()` to use `await self.socket_client.reject_job()`
- [ ] Remove direct store access and `_find_job()` method

**Files:**
- `src/alfred/tools/reject_job.py`

**Test:**
- [ ] Write test: `test_reject_job_uses_socket_client()`

---

### Phase 3: Update Tool Registration

#### 3.1 Update register_builtin_tools()
- [ ] Add `socket_client` parameter to function signature
- [ ] Update cron tool registration to use `socket_client` instead of `scheduler`
- [ ] Update docstring

**Files:**
- `src/alfred/tools/__init__.py`

#### 3.2 Update Alfred class
- [ ] Create and start `SocketClient` in `Alfred.start()`
- [ ] Stop `SocketClient` in `Alfred.stop()`
- [ ] Pass `socket_client` to `register_builtin_tools()`

**Files:**
- `src/alfred/alfred.py`

#### 3.3 Update main.py TUI initialization
- [ ] Create `SocketClient` for tools (separate from cron runner's client)
- [ ] Pass socket client to `Alfred` or `register_builtin_tools()`

**Files:**
- `src/alfred/cli/main.py`

---

### Phase 4: Integration Testing

#### 4.1 End-to-End Tests
- [ ] Test: Submit job via tool → Verify daemon receives request
- [ ] Test: Approve job via tool → Verify job activated
- [ ] Test: List jobs via tool → Verify current data returned
- [ ] Test: Reject job via tool → Verify job deleted

#### 4.2 Error Handling Tests
- [ ] Test: Tool fails gracefully when daemon not running
- [ ] Test: Tool handles timeout from daemon
- [ ] Test: Tool handles invalid job identifier

---

## Implementation Notes

### Design Decisions

1. **Two SocketClients**: The TUI needs one `SocketClient` for tools to send requests to the daemon, and the daemon has its own `SocketClient` to send notifications to the TUI. Both connect to the same socket path.

2. **Synchronous Tool Interface**: Tools use `async def execute_stream()` but the socket operations are async. The socket client methods are already async, so this aligns well.

3. **Job Lookup in Daemon**: The daemon handles job ID/name lookup, simplifying tools. Tools just pass the identifier as provided by the user.

### Potential Issues

1. **Circular Import**: `SocketClient` imports from `socket_protocol`, and tools will import `SocketClient`. Need to ensure no circular imports.

2. **Socket Connection Timing**: Tools may be called before socket client is connected. Need to handle "not connected" gracefully.

3. **Response Timeout**: Default timeout of 5-10 seconds should be sufficient for job operations.

---

## Success Criteria

- [ ] All 4 cron tools use `SocketClient` instead of `CronScheduler`
- [ ] SocketServer handles all job management requests
- [ ] Tests pass: `uv run pytest tests/tools/test_cron_tools.py -v`
- [ ] Manual test: Submit, approve, list, reject jobs via TUI
- [ ] No direct database access from tools

---

*Created: 2026-03-08*
*PRD: #120 - Milestone 4*
