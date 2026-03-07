# Alfred Cron System

The cron system provides scheduled job execution with TUI integration, observability, and resource limits.

## Architecture Overview

```
┌─────────────────┐      Unix Socket       ┌─────────────────┐
│   TUI (pi)      │ ◄────────────────────► │  Cron Runner    │
│                 │   JSON messages        │  (daemon)       │
│  - SocketServer │                        │                 │
│  - Displays     │                        │  - Scheduler    │
│    notifications│                        │  - Executor     │
└─────────────────┘                        └─────────────────┘
         │                                          │
         │         SQLite Database                  │
         └──────────────────────────────────────────┘
                    (jobs, executions, logs)
```

## Components

### 1. Scheduler (`scheduler.py`)

The main orchestrator that:
- Manages job registration and persistence
- Monitors schedules (every 60s by default)
- Triggers job execution via `asyncio.create_task()`
- Provides job approval workflow for user-submitted jobs

Key methods:
- `register_job()` - Add a job to the schedule
- `submit_user_job()` - Submit for approval (with linting)
- `approve_job()` - Activate a pending job
- `start()` / `stop()` - Control the scheduler loop

### 2. Executor (`executor.py`)

Wraps job execution with:
- **Timeout enforcement** - Kills jobs exceeding time limit
- **Memory monitoring** - Tracks peak memory usage
- **Output capture** - Captures stdout/stderr with truncation
- **Safe namespace** - Injects `notify()` function into job globals

Resource limits per job:
- Timeout: 300s (5 min) default
- Max memory: 512 MB
- Max output lines: 1000

### 3. Socket Protocol (`socket_protocol.py`)

**Unix Domain Socket** (not TCP) at `~/.cache/alfred/notify.sock`

Message format: **JSON + newline delimiter**

```json
{"type": "notify", "message": "Hello", "level": "info", "timestamp": "2024-01-01T00:00:00"}
```

Message types:
- **Notifications**: `notify` (toast messages)
- **Job lifecycle**: `job_started`, `job_completed`, `job_failed`
- **Runner lifecycle**: `runner_started`, `runner_stopping`
- **Health checks**: `ping` / `pong`
- **Queries**: `query_jobs` / `query_jobs_response`

### 4. Socket Server (`socket_server.py`)

Runs in TUI process, receives messages from cron runner:
- Displays toast notifications
- Updates job status in UI
- Responds to queries (job status requests)

Callbacks:
- `on_notify` - Show toast notification
- `on_job_started/completed/failed` - Update job status UI
- `on_query_jobs` - Provide live job status

### 5. Socket Client (`socket_client.py`)

Used by cron runner to send messages:
- Auto-connects with retry logic
- Buffers messages when disconnected
- Provides `notify()` helper for jobs

### 6. Job Linter (`job_linter.py`)

**AST-based static analysis** that detects foot guns:

Blocking calls (rejected):
- `subprocess.run()` - Use `asyncio.create_subprocess_exec()`
- `time.sleep()` - Use `asyncio.sleep()`
- `requests.get/post()` - Use `aiohttp` or `httpx`
- `os.system()` - Use asyncio subprocess
- `open()` - Use `aiofiles` for file I/O
- `input()` - Never use in cron jobs

Wrong patterns (rejected):
- `subprocess.run(['notify', ...])` - Use injected `await notify()`

Integration:
- Runs on `submit_user_job()`
- Runs on `approve_job()`
- Returns clear error messages with suggestions

### 7. Store (`store.py`)

SQLite persistence:
- `jobs` table - Job definitions and status
- `executions` table - Execution history with output
- Methods: `save_job()`, `load_jobs()`, `record_execution()`

### 8. System Jobs (`system_jobs.py`)

Built-in jobs that don't require approval:
- `session_ttl` - Session compaction (every 5 min)
- `session_summarizer` - Auto-summarize idle sessions

## Communication Flow

### Notification (fire-and-forget)

```
Cron Runner          TUI (SocketServer)
     │                       │
     │  {"type": "notify"}   │
     │──────────────────────>│
     │                       │
     │                       │─► Show toast
```

### Query/Response (request-response)

```
TUI/Context            Cron Runner
     │                       │
     │  {"type": "query_jobs"} │
     │──────────────────────>│
     │                       │─► Query scheduler
     │                       │
     │  {"type": "query_jobs_response"}
     │<──────────────────────│
```

## Job Execution Flow

1. **Schedule Check** (every 60s)
   ```python
   for job in jobs:
       if should_run(job.expression, job.last_run):
           asyncio.create_task(execute_job(job))  # Non-blocking
   ```

2. **Execution** (in JobExecutor)
   ```python
   async with job._running:  # Prevents concurrent runs
       result = await executor.execute()
       # Timeout, memory monitoring, output capture
   ```

3. **Notification** (via socket)
   ```python
   await socket_client.send(JobCompletedMessage(...))
   ```

4. **Persistence**
   ```python
   await store.record_execution(record)
   ```

## Security Model

- Jobs run in isolated asyncio task (not subprocess)
- `__builtins__` available but no filesystem access by default
- `notify()` injected for safe TUI communication
- Code linting prevents common blocking patterns
- User jobs require approval before activation

## Configuration

```toml
[cron]
enabled = true
check_interval = 60  # Seconds between schedule checks
socket_path = "~/.cache/alfred/notify.sock"

[cron.limits]
timeout_seconds = 300
max_memory_mb = 512
max_output_lines = 1000
```

## Testing

```bash
# Run cron tests
uv run pytest tests/cron/ -v

# Run linter tests
uv run pytest tests/test_job_linter.py -v
```

## Common Issues

### "No such file or directory: 'notify'"

Job is using `subprocess.run(['notify', ...])` instead of the injected `await notify()`. The linter should catch this.

### TUI freezes during job execution

Job is using blocking calls (`time.sleep`, `subprocess.run`). The linter should catch this.

### Socket connection refused

TUI isn't running or socket file is stale. Cron runner will buffer messages and retry.

## Adding New Message Types

1. Add to `MessageType` enum in `socket_protocol.py`
2. Create dataclass inheriting from `SocketMessage`
3. Add dispatch case in `SocketMessage.from_json()`
4. Add handler in `SocketServer._dispatch_message()`
5. Add send method in `SocketClient` (if needed)
