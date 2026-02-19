# PRD: Cron Scheduler System

**Issue**: #68  
**Status**: In Progress  
**Priority**: High  
**Created**: 2026-02-18

---

## Problem Statement

Alfred needs a reliable way to run background tasks—session TTL checks, memory compaction, and user-scheduled jobs. Without a proper cron system, these tasks must be manually triggered or awkwardly piggybacked on user interactions. This limits automation, delays critical maintenance, and prevents users from scheduling their own recurring workflows.

---

## Solution Overview

Build a production-grade cron scheduler with:

1. **Standard cron syntax** (`0 19 * * 0` for Sunday 7pm)
2. **Persistent job storage** in `data/cron.jsonl` with full history in `data/cron_history.jsonl`
3. **Comprehensive observability**—logging, metrics, health checks, and alerts
4. **Safe user jobs** with human code review and approval
5. **Queue-based concurrency**—jobs queue if already running, never skip

---

## Design Principles

### 1. Human-in-the-Loop for User Jobs
All user-created jobs require explicit human review and approval before execution. The model can generate code, but a human must approve it. This is the primary security mechanism.

### 2. Audit Everything
Every job execution is logged with full context—code snapshot, inputs, outputs, duration, success/failure. Post-hoc analysis is always possible.

### 3. Fail Fast, Alert Loudly
Job failures surface immediately through logging and alerts. Silent failures hide bugs.

### 4. Defense in Depth
Human approval is primary. Secondary defenses: timeouts, memory limits, optional network restrictions, and audit trails.

---

## Technical Architecture

### Core Components

#### 1. CronScheduler (`src/cron/scheduler.py`)

The orchestrator that manages job lifecycle.

```python
class CronScheduler:
    """Async job scheduler with cron-based execution."""
    
    def __init__(self, check_interval: float = 60.0):
        self._jobs: dict[str, Job] = {}
        self._task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._check_interval = check_interval
    
    async def start(self) -> None:
        """Start the scheduler monitoring loop."""
        
    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        
    def register_job(self, job: Job) -> None:
        """Register a job for execution."""
```

**Job dataclass:**
```python
@dataclass
class Job:
    job_id: str
    name: str
    expression: str
    handler: Callable[[], Awaitable[None]]
    status: JobStatus = JobStatus.ACTIVE
    last_run: datetime | None = None
    _running: asyncio.Lock = field(default_factory=asyncio.Lock)
```

#### 2. CronStore (`src/cron/store.py`)

JSONL persistence for jobs and execution history.

**File: `data/cron.jsonl`**
```json
{
  "job_id": "uuid",
  "name": "Session TTL Check",
  "description": "Check for expired sessions and trigger summarization",
  "cron": "*/5 * * * *",
  "code": "async def run(context): ...",
  "job_type": "system",
  "status": "active",
  "created_at": "2026-02-18T10:00:00Z",
  "updated_at": "2026-02-18T10:00:00Z",
  "resource_limits": {
    "timeout_seconds": 30,
    "max_memory_mb": 100,
    "allow_network": false
  }
}
```

**File: `data/cron_history.jsonl`**
```json
{
  "execution_id": "uuid",
  "job_id": "uuid",
  "started_at": "2026-02-18T10:05:00Z",
  "ended_at": "2026-02-18T10:05:02Z",
  "status": "success",
  "code_snapshot": "async def run(context): ...",
  "stdout": "...",
  "stderr": "...",
  "duration_ms": 1500,
  "memory_peak_mb": 45
}
```

#### 3. CronParser (`src/cron/parser.py`)

Standard cron expression parsing using stateless utility functions.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

def is_valid(expression: str) -> bool:
    """Validate if a string is a valid cron expression."""
    
def get_next_run(
    expression: str,
    from_time: datetime | None = None,
    timezone: str = "UTC",
) -> datetime:
    """Get the next execution time for a cron expression.
    
    Returns timezone-aware datetime in the target timezone.
    """
    
def should_run(
    expression: str,
    last_run: datetime,
    current_time: datetime,
) -> bool:
    """Check if a job should run based on last execution time.
    
    Returns True if scheduled time passed since last_run (catch-up behavior).
    """
```

Supports standard cron syntax (5 fields only):
- `*/5 * * * *` — every 5 minutes
- `0 19 * * 0` — Sunday at 7pm
- `0 9 * * 1-5` — weekdays at 9am
- `0 0 1 * *` — first of month at midnight

#### 4. JobExecutor (`src/cron/executor.py`)

Isolated execution environment with resource limits.

```python
class JobExecutor:
    """Execute jobs with resource limits and monitoring."""
    
    def __init__(self, job: Job, context: ExecutionContext):
        self.job = job
        self.context = context
        self.limits = job.resource_limits
    
    async def execute(self) -> ExecutionResult:
        """Execute job with timeout and memory monitoring."""
        # Inject safe globals
        # Run with asyncio.wait_for(timeout)
        # Capture stdout/stderr
        # Record memory usage
```

**Injected globals for user jobs:**
```python
{
    "remember": lambda text: context.memory.add(text),
    "search": lambda query: context.memory.search(query),
    "notify": lambda msg: context.notifier.send(msg),
    "store_get": lambda key: context.kv.get(key),
    "store_set": lambda key, val: context.kv.set(key, val),
    # No os, subprocess, open by default—user must import if needed
}
```

#### 5. Observability Stack (`src/cron/observability.py`)

**Logging:**
- Job start/end with structured logging
- Duration, memory, success/failure
- Full code snapshot for audit

**Metrics:**
- Jobs executed (counter)
- Job duration (histogram)
- Job failures (counter, labeled by job_id and error type)
- Queue depth (gauge)
- Scheduler uptime (gauge)

**Health Checks:**
```python
class HealthChecker:
    async def check(self) -> HealthStatus:
        # Is scheduler running?
        # Any jobs stuck > timeout?
        # Storage accessible?
```

**Alerts:**
```python
class AlertManager:
    async def check_and_alert(self) -> None:
        # Job failed N times in a row
        # Job execution time > threshold
        # Scheduler not running
```

---

## Job Types

### System Jobs

Pre-approved jobs built into Alfred. Signed by codebase, no human review needed.

| Job | Cron | Description |
|-----|------|-------------|
| session_ttl | `*/5 * * * *` | Check for expired sessions, trigger summarization |
| memory_compact | `0 2 * * *` | Compact old memories, extract insights |
| memory_cleanup | `0 3 * * 0` | Remove orphaned memory entries |
| health_report | `0 9 * * *` | Daily system health summary |

### User Jobs

Created by users through natural language, code generated by model, human approval required.

**Example user interaction:**
```
User: "Remind me every morning at 8am to check my calendar"
Alfred: "I'll create a job that sends you a notification at 8am daily. 
         Here's the code:
         
         async def run(context):
             await context.notify("Time to check your calendar!")
         
         Approve this job? (yes/no)"
User: "yes"
Alfred: "Job approved and scheduled."
```

**User job lifecycle:**
```
Created → Pending Review → Approved → Active → (Executes on schedule)
   ↑                          ↓
   └────── Rejected ←─────────┘
```

---

## Concurrency Model

### Queue-Based Execution

Jobs never skip. If a job is still running when next schedule arrives, the new execution queues.

```python
class JobQueue:
    """Per-job queue for serialized execution."""
    
    def __init__(self):
        self._running: asyncio.Task | None = None
        self._queued: list[asyncio.Task] = []
    
    async def enqueue(self, coro: Coroutine) -> None:
        """Add execution to queue."""
        if self._running is None:
            self._running = asyncio.create_task(self._run(coro))
        else:
            self._queued.append(asyncio.create_task(coro))
    
    async def _run(self, coro: Coroutine) -> None:
        """Execute and process queue."""
        try:
            await coro
        finally:
            self._running = None
            if self._queued:
                next_coro = self._queued.pop(0)
                self._running = asyncio.create_task(self._run(next_coro))
```

---

## Security Model

### Primary: Human Approval

All user jobs require explicit approval before execution.

```python
async def submit_user_job(self, name: str, description: str, 
                          cron: str, code: str) -> str:
    job = UserJob(
        job_id=str(uuid4()),
        name=name,
        description=description,
        cron=cron,
        code=code,
        status="pending",
        created_at=datetime.now(UTC)
    )
    await self.store.save_job(job)
    
    # Notify for approval
    await self.notifier.send(
        f"Job '{name}' pending approval. Review: /cron review {job.job_id}"
    )
    return job.job_id
```

### Secondary: Resource Limits

```python
@dataclass
class ResourceLimits:
    timeout_seconds: int = 30
    max_memory_mb: int = 100
    allow_network: bool = False
    max_output_lines: int = 1000
```

### Tertiary: Audit Trail

Every execution logged with:
- Full code snapshot (what actually ran)
- Input parameters
- stdout/stderr
- Duration and memory
- Success/failure status

---

## Context Integration

### Alfred Lifecycle

```python
class Alfred:
    def __init__(self, config: Config):
        # ... existing init ...
        
        self.cron_scheduler = CronScheduler(
            store=CronStore(config.data_dir),
            notifier=self.notifier
        )
        
        # Register system jobs
        self.cron_scheduler.register_system_job(SystemJob(
            name="session_ttl",
            cron="*/5 * * * *",
            handler=self._check_session_ttl
        ))
    
    async def start(self) -> None:
        """Start Alfred and all subsystems."""
        await self.cron_scheduler.start()
    
    async def stop(self) -> None:
        """Graceful shutdown."""
        await self.cron_scheduler.stop()
```

### Natural Language Interface

Users interact with Alfred conversationally. No `/commands` required.

**Creating jobs:**
```
User: "Remind me every morning at 8am to check my calendar"
Alfred: "I'll create a job that sends you a notification at 8am daily. 
         Here's the code:
         
         async def run(context):
             await context.notify("Time to check your calendar!")
         
         Approve this job? (yes/no)"
User: "yes"
Alfred: "Job approved and scheduled."
```

**Managing jobs:**
```
User: "What jobs do I have running?"
Alfred: "You have 3 active jobs:
         1. Daily calendar reminder (8am)
         2. Weekly summary (Sundays 7pm)
         3. Session cleanup (every 5 min)"

User: "Cancel the calendar reminder"
Alfred: "Deleted job 'Daily calendar reminder'."
```

**Reviewing executions:**
```
User: "Did my weekly summary run last Sunday?"
Alfred: "Yes, it ran at 7:00pm and completed successfully in 2.3 seconds."
```

### CLI Interface (Optional)

```bash
# List all jobs
alfred cron list

# Submit new job
alfred cron submit "Daily summary" "0 9 * * *" "async def run(ctx): ..."

# Review pending job
alfred cron review <job_id>

# Approve/reject
alfred cron approve <job_id>
alfred cron reject <job_id>

# View history
alfred cron history <job_id>

# System metrics
alfred cron metrics
```

---

## Milestone Roadmap

| # | Milestone | Description | Success Criteria |
|---|-----------|-------------|------------------|
| M1 | **Core Scheduler** | ✅ Complete | Async scheduler with job registration, execution loop, 13 tests, 92% coverage |
| M2 | **Cron Parser** | ✅ Complete | Standard cron expression parsing using `croniter` library, 25 tests, 90% coverage |
| M3 | **Persistence** | ✅ Complete | JSONL storage with atomic writes, 19 tests, 94% coverage, documentation created |
| M4 | **Observability** | Logging, metrics, health checks, alerts | All jobs logged, metrics exposed, alerts fire |
| M5 | **System Jobs** | ✅ Complete | Session TTL job runs every 5 min, auto-registers on startup, 8 tests, 100% coverage |
| M6 | **User Job Submission** | Model generates code, submits for review | User can create job via natural language |
| M7 | **Approval Workflow** | ✅ Complete | ListJobsTool, ApproveJobTool, RejectJobTool, 18 tests, fuzzy name matching |
| M8 | **Resource Limits** | ✅ Complete | Timeout enforcement, memory monitoring, output limits, 31 tests, 95% coverage |
| M9 | **Natural Language Interface** | ✅ Complete | Rule-based NL parser, 52 tests, timezone support, confidence scoring |
| M10 | **CLI Integration** | alfred cron commands for power users | Optional CLI management available |
| M11 | **Testing** | ✅ Complete | 214 tests, integration workflows, e2e tests, race condition fixed |
| M12 | **ScheduleJobTool** | ✅ Complete | Tool for agent to create cron jobs, 14 tests (unit + integration), Pydantic validation |

---

## Success Criteria

- [ ] Jobs execute reliably on schedule (99.9% uptime)
- [ ] No job skips—queue handles overlapping executions
- [ ] All executions logged with full audit trail
- [ ] Alerts fire within 60 seconds of job failure
- [ ] User jobs require human approval before first run
- [ ] Resource limits enforced (timeout, memory)
- [ ] System survives restart without losing job state
- [ ] All system jobs (TTL, compaction, cleanup) running
- [ ] User can create, review, approve jobs via natural language
- [ ] Test coverage >90%

---

## File Structure

```
src/
├── cron/
│   ├── __init__.py
│   ├── scheduler.py       # Core scheduler orchestration
│   ├── store.py           # JSONL persistence
│   ├── parser.py          # Cron expression parsing
│   ├── nlp_parser.py      # Natural language to cron parsing
│   ├── executor.py        # Job execution with limits
│   ├── observability.py   # Logging, metrics, health, alerts
│   ├── models.py          # Job, ExecutionResult, etc.
│   └── system_jobs.py     # Built-in system job handlers
├── tools/
│   ├── schedule_job.py    # Create jobs via natural language
│   ├── list_jobs.py       # List jobs by status
│   ├── approve_job.py     # Approve pending jobs
│   └── reject_job.py      # Reject/delete jobs
data/
├── cron.jsonl             # Job definitions
└── cron_history.jsonl     # Execution history
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `croniter` | Cron expression parsing—standard syntax support |
| `psutil` | Memory monitoring during job execution |
| `prometheus_client` | Metrics export (optional) |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | Human approval for user jobs | Primary security mechanism—sandboxing Python is unreliable |
| 2026-02-18 | Standard cron syntax | Industry standard, well understood, no need for custom DSL |
| 2026-02-18 | Queue-based concurrency | Never skip jobs, preserve execution order |
| 2026-02-18 | Separate history JSONL | Query performance, audit compliance, easy archival |
| 2026-02-18 | System vs User job distinction | System jobs trusted, user jobs reviewed |
| 2026-02-18 | Resource limits secondary | Human approval catches intent, limits catch accidents |
| 2026-02-18 | Use `croniter` library | Battle-tested, handles edge cases (leap years, DST, etc.) |
| 2026-02-18 | Stateless utility functions | `is_valid()`, `get_next_run()`, `should_run()`—simpler API, easier testing |
| 2026-02-18 | 5-field cron validation | Reject expressions with fewer or more than 5 fields (minute hour day month dow) |
| 2026-02-18 | Timezone-aware return values | `get_next_run()` returns datetime in target timezone (e.g., 9am NY), not UTC |
| 2026-02-18 | Missed window catch-up | `should_run()` returns True if scheduled time passed since last run—jobs don't skip |
| 2026-02-19 | Rule-based natural language parsing | Regex patterns for 90% of cases, faster than LLM, extensible, no token costs |
| 2026-02-19 | asyncio.Lock in CronStore | Prevents race conditions between scheduler execution and test code accessing files |

---

## Open Questions (Resolved)

**Q: How do we handle daylight saving time transitions?**  
A: Store all times in UTC. Cron expressions interpreted as UTC.

**Q: What happens if the scheduler is down during a scheduled time?**  
A: Job runs immediately on startup if missed (configurable per-job).

**Q: Can jobs be edited after creation?**  
A: Yes, but edited user jobs return to "pending" status for re-approval.

**Q: How do we prevent job storms on startup?**  
A: Max 1 queued execution per job—if multiple missed, only run once.
