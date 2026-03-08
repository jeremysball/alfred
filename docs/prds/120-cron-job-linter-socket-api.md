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
- [x] Create new `protocol.py` with Pydantic dataclasses and manual routing
- [ ] Implement server dispatch handlers in daemon
- [ ] Test query/response flow end-to-end

**Files Modified/Created**:
- `src/alfred/cron/socket_protocol.py`
- `src/alfred/cron/socket_client.py`
- `src/alfred/cron/protocol.py` (new - Pydantic dataclasses with validation)

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

### Milestone 5: Alfred Decoupling ✅
**Status**: Complete

- [x] Remove `CronScheduler` initialization from `Alfred.start()/stop()`
- [x] Ensure Alfred TUI doesn't depend on cron scheduler
- [x] Convert `daemon-*` commands to `daemon` subcommand group
- [x] Add `alfred daemon logs` command

**Files Modified**:
- `src/alfred/alfred.py` - Removed cron scheduler start/stop
- `src/alfred/cli/main.py` - Restructured daemon commands
- `src/alfred/cli/cron.py` - Updated to use socket client

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

### Decision: Socket Protocol Type Safety (Updated)

**Choice**: Use `pydantic.dataclasses` with manual `match/case` routing.

**Rejected**:
- Hand-rolled JSON dicts - No type safety, runtime errors
- `TypedDict` - No validation, awkward with unions  
- `NamedTuple` - Immutable (problematic), no JSON support
- `BaseModel` + discriminated unions - Too much magic, complex

**Selected**: `pydantic.dataclasses` with explicit routing:

```python
from pydantic.dataclasses import dataclass

@dataclass
class JobStarted:
    job_id: str
    job_name: str
    timestamp: datetime
    msg_type: Literal["job_started"] = "job_started"

# Explicit routing - clear and extensible
def parse_message(data: str) -> SocketMessage:
    parsed = json.loads(data)
    match parsed["msg_type"]:
        case "job_started":
            return JobStarted(**parsed)
        case "jobs_response":
            return _parse_jobs_response(parsed)
```

Benefits:
- IDE autocomplete
- Validation at instantiation
- No magic - explicit routing
- Easy to extend

### Decision: Type Reuse with Existing Models

**Problem**: `alfred.cron.models` already has `Job` and `ExecutionRecord` dataclasses.

**Choice**: Create converter methods rather than duplicating fields.

```python
@dataclass
class JobInfo:
    job_id: str
    name: str
    # ... fields match Job dataclass

    @classmethod
    def from_job(cls, job: Job) -> JobInfo:
        """Convert existing dataclass to Pydantic model."""
        return cls(job_id=job.job_id, name=job.name, ...)
```

**Why not use dataclasses directly?**
- Pydantic provides JSON validation automatically
- Dataclasses don't support discriminated unions
- Converters are explicit and testable

### Decision: Event Notification Types

**Choice**: Separate lightweight event types for notifications.

**Rationale**: Full `JobInfo` is overkill for notifications:

```python
# Event - minimal data for notification
class JobStarted:
    job_id: str
    job_name: str
    timestamp: datetime

# Response - full data for display  
class JobsResponse:
    jobs: list[JobInfo]  # Full details
```

This keeps socket traffic minimal while maintaining type safety.

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
- `src/alfred/cron/protocol.py` - Pydantic dataclass socket protocol

**Modified Files**:
- `src/alfred/cron/scheduler.py` - Integrated linter
- `src/alfred/cron/socket_protocol.py` - Added new message types
- `src/alfred/cron/socket_client.py` - Added API methods
- `src/alfred/cron/socket_server.py` - Partial implementation
- `src/alfred/session.py` - Fixed tool_calls conversion
- `src/alfred/alfred.py` - Removed cron scheduler start/stop
- `src/alfred/cli/main.py` - Restructured daemon commands
- `src/alfred/cli/cron.py` - Updated to use socket client

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

## Milestone 8: TUI Event System with Subscription-Based Routing 🔄

**Status**: Design Complete, Implementation Pending

Add a type-safe event system inside the TUI that allows components to subscribe to specific daemon events. The daemon pushes notifications through the socket, and the TUI routes them to handlers based on event type.

### Event System Design

#### Single Socket, Subscription Model

Both TUI and CLI connect to the **same daemon socket**, but behave differently:

**TUI (Long-lived connection with subscription):**
```python
# TUI connects and stays connected for notifications
reader, writer = await asyncio.open_unix_connection("daemon.sock")

# Subscribe to specific event types
writer.write(json.dumps({
    "cmd": "subscribe",
    "events": ["job_started", "job_completed", "job_failed"]
}) + "\n")

# Event loop - daemon pushes notifications asynchronously
while True:
    line = await reader.readline()
    event = json.loads(line)
    event_bus.publish(event["type"], event)  # Route to handlers
```

**CLI (Short-lived request/response):**
```python
# CLI connects, sends command, gets response, disconnects
reader, writer = await asyncio.open_unix_connection("daemon.sock")
writer.write(json.dumps({"cmd": "list_jobs"}) + "\n")
response = await reader.readline()  # Immediate response
writer.close()
```

#### TUI Event Bus Architecture

```
┌─────────────────────────────────────────────┐
│                  TUI                        │
│  ┌─────────────────────────────────────┐   │
│  │         EventBus (singleton)        │   │
│  │  ┌───────────────────────────────┐  │   │
│  │  │  handlers: dict[type, list]   │  │   │
│  │  │  - JobStartedEvent: [toast]   │  │   │
│  │  │  - JobCompleted: [toast, db]  │  │   │
│  │  └───────────────────────────────┘  │   │
│  │                                     │   │
│  │  subscribe(EventType, handler)      │   │
│  │  publish(event) → route to handlers │   │
│  └─────────────────────────────────────┘   │
│                     ▲                       │
│                     │                       │
│  ┌──────────┐  ┌───┴────────┐  ┌─────────┐ │
│  │ToastMgr  │  │JobHistory  │  │StatusBar│ │
│  │subscribe │  │subscribe   │  │subscribe│ │
│  │(JobEvent)│  │(AllEvents) │  │(Status) │ │
│  └──────────┘  └────────────┘  └─────────┘ │
└─────────────────────────────────────────────┘
```

#### Handler Registration by Event Type

Handlers declare which concrete event they handle via type hints. All data is fully typed - no `dict[str, Any]` anywhere.

**Decision: Strong Typing vs Dynamic Dicts**

Rejected approaches:
- `dict[str, Any]` - No IDE support, runtime errors, hard to refactor
- `TypedDict` - Better but still no validation, awkward inheritance
- `NamedTuple` - Immutable (problematic for updates), no validation

Selected: **`pydantic.dataclasses`** with explicit `match/case` routing

```python
from pydantic.dataclasses import dataclass
from typing import Literal
from dataclasses import asdict
import json

# Fully typed data models with dataclass syntax
@dataclass
class JobInfo:
    job_id: str
    name: str
    status: Literal["pending", "active", "paused"]
    expression: str
    code: str
    created_at: datetime
    resource_limits: dict

@dataclass
class JobStarted:
    job_id: str
    job_name: str
    timestamp: datetime
    msg_type: Literal["job_started"] = "job_started"

# Convert from existing dataclass (no duplication!)
@classmethod
def from_job(cls, job: Job) -> JobInfo:
    return cls(
        job_id=job.job_id,
        name=job.name,
        # ...
    )

# Serialize nested dataclasses
def serialize_message(msg: SocketMessage) -> str:
    return json.dumps(asdict(msg), default=str) + "\n"

# Explicit routing - easy to understand and extend
def parse_message(data: str) -> SocketMessage:
    parsed = json.loads(data)
    match parsed["msg_type"]:
        case "job_started":
            return JobStarted(**parsed)
        case "jobs_response":
            return _parse_jobs_response(parsed)
        # ... explicit cases for each type
```

Benefits:
- IDE autocomplete on all fields
- Type checking catches errors at development time
- Validation at instantiation time
- No magic - explicit routing is clear
- Easy to extend with new message types
- Converter pattern avoids field duplication

#### Handler Registration by Event Type

Handlers declare which concrete event they handle via type hints:

```python
from dataclasses import dataclass
from typing import Protocol, TypeVar

# Event types (dataclasses for type safety)
@dataclass
class JobStartedEvent:
    job_id: str
    job_name: str
    timestamp: datetime

@dataclass
class JobCompletedEvent:
    job_id: str
    job_name: str
    duration_ms: int
    stdout_preview: str

@dataclass
class JobFailedEvent:
    job_id: str
    job_name: str
    error: str
    duration_ms: int

# Handler protocol - type-safe subscription
T = TypeVar('T')
EventHandler = Callable[[T], None]

class EventBus:
    def __init__(self):
        self._handlers: dict[type, list[Callable]] = {}
    
    def subscribe(self, event_type: type[T], handler: EventHandler[T]) -> None:
        """Subscribe handler to specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event: object) -> None:
        """Route event to all handlers for its type."""
        event_type = type(event)
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler failed for {event_type}: {e}")

# Usage - handlers specify concrete event type
class ToastManager:
    def __init__(self, event_bus: EventBus):
        # Subscribe to specific events with type-safe handlers
        event_bus.subscribe(JobStartedEvent, self._on_job_started)
        event_bus.subscribe(JobCompletedEvent, self._on_job_completed)
        event_bus.subscribe(JobFailedEvent, self._on_job_failed)
    
    def _on_job_started(self, event: JobStartedEvent) -> None:
        self.add(f"Job started: {event.job_name}", "info")
    
    def _on_job_completed(self, event: JobCompletedEvent) -> None:
        self.add(f"Job completed: {event.job_name} ({event.duration_ms}ms)", "info")
    
    def _on_job_failed(self, event: JobFailedEvent) -> None:
        self.add(f"Job failed: {event.job_name} - {event.error}", "error")

class JobHistoryPanel:
    def __init__(self, event_bus: EventBus):
        # Subscribe to all job lifecycle events
        event_bus.subscribe(JobStartedEvent, self._add_entry)
        event_bus.subscribe(JobCompletedEvent, self._add_entry)
        event_bus.subscribe(JobFailedEvent, self._add_entry)
    
    def _add_entry(self, event: JobStartedEvent | JobCompletedEvent | JobFailedEvent) -> None:
        self.entries.append(event)
        self.refresh()
```

#### Socket Message Routing

```python
# Daemon socket handler
async def handle_client(reader, writer):
    client_subscriptions: set[type] = set()
    
    while True:
        line = await reader.readline()
        msg = json.loads(line)
        
        if msg["cmd"] == "subscribe":
            # Store subscription for this client
            for event_name in msg["events"]:
                event_type = EVENT_NAME_TO_TYPE[event_name]
                client_subscriptions.add(event_type)
                subscribers[event_type].add(writer)
                
        elif msg["cmd"] == "list_jobs":
            # Immediate response
            writer.write(json.dumps({"jobs": [...]}) + "\n")
            await writer.drain()

# When event occurs, push to subscribers
async def on_job_completed(job_result):
    event = JobCompletedEvent(...)
    
    # Persist to DB
    await db.save_execution(event)
    
    # Push to all subscribers
    for subscriber in subscribers.get(JobCompletedEvent, set()):
        subscriber.write(json.dumps(event.to_dict()) + "\n")
        await subscriber.drain()
    
    # Also publish to TUI event bus
    event_bus.publish(event)
```

#### Comparison: With vs Without Polling

| Aspect | With Polling | Without Polling (Selected) |
|--------|--------------|---------------------------|
| **Latency** | 1-5 seconds | Instant (push) |
| **CPU/Battery** | Higher (constant requests) | Lower (idle until event) |
| **Complexity** | Simpler | Medium (connection management) |
| **Reliability** | Works through restarts | Needs reconnection logic |
| **Scale** | Poor (N clients × poll rate) | Excellent (event-driven) |

**Selected**: Without polling for instant notifications and efficiency.

### Tasks

- [ ] Create `EventBus` class with type-safe subscribe/publish
- [ ] Add event dataclasses (`JobStartedEvent`, `JobCompletedEvent`, etc.)
- [ ] Add subscription protocol to daemon socket server
- [ ] Add event routing in daemon (push to subscribers)
- [ ] Integrate `EventBus` into TUI initialization
- [ ] Migrate `ToastManager` to use event subscription
- [ ] Add reconnection logic for TUI socket client
- [ ] Add heartbeat/ping to detect dead connections
- [ ] Write tests for event routing

**Files to Create/Modify**:
- `src/alfred/cron/protocol.py` (new - Pydantic socket protocol with discriminated unions)
- `src/alfred/interfaces/event_bus.py` (new - Type-safe event bus)
- `src/alfred/cron/daemon_runner.py` (add socket server with subscription handling)
- `src/alfred/interfaces/pypitui_cli.py` (integrate event bus)
- `src/alfred/interfaces/pypitui/toast.py` (subscribe to events)
- `src/alfred/cron/socket_server.py` (update to use new protocol)
- `src/alfred/cron/socket_client.py` (update to use new protocol)

---


---

*Last Updated: 2026-03-08*
