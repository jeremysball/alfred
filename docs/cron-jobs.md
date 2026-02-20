# Cron Jobs Documentation

## Overview

Alfred's cron system allows scheduling recurring tasks. Jobs run in the background at specified intervals using standard cron syntax or natural language.

## Creating a Job

### Using CLI

```bash
# Submit a job for approval
alfred cron submit "Daily Standup" "0 9 * * 1-5" "async def run(): await notify('Time for standup!')"

# List all jobs
alfred cron list

# Approve a pending job
alfred cron approve <job-id>

# Reject a pending job
alfred cron reject <job-id>
```

### Natural Language Scheduling

Alfred can parse natural language expressions:

- "every day at 9am"
- "every monday at 2pm"
- "every 30 minutes"
- "weekdays at 9am"

### Job Structure

```python
from src.cron.models import Job

job = Job(
    job_id="unique-id",          # Unique identifier
    name="Human-readable name",   # Display name
    expression="*/5 * * * *",     # Cron: every 5 minutes
    code="""
async def run():
    # Your code here
    await notify("Hello from cron!")
""",
    status="active",              # active, pending, or paused
)
```

### Available Functions in Job Code

Jobs can use these built-in functions:

- `notify(message)` - Send notification to user
- `print()` - Log output (captured to execution history)

### Cron Expression Format

Standard 5-field cron syntax:

```
* * * * *
│ │ │ │ │
│ │ │ │ └─ Day of week (0-7, 0=Sunday)
│ │ │ └─── Month (1-12)
│ │ └───── Day of month (1-31)
│ └─────── Hour (0-23)
└───────── Minute (0-59)
```

Examples:
- `*/5 * * * *` - Every 5 minutes
- `0 9 * * 1-5` - Weekdays at 9am
- `0 0 * * *` - Daily at midnight
- `0 19 * * 0` - Sundays at 7pm

### Registering a Job

```python
from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore

# Create scheduler with persistence
store = CronStore()
scheduler = CronScheduler(store=store)

# Register job
scheduler.register_job(job)

# Start scheduler
await scheduler.start()
```

### User-Created Jobs

For user-created jobs, submit for approval first:

```python
# Submit job (goes to pending status)
job_id = await scheduler.submit_user_job(
    name="Daily reminder",
    expression="0 9 * * *",
    code="async def run(): await notify('Good morning!')",
)

# Approve job
await scheduler.approve_job(job_id, approved_by="admin")
```

## Job Lifecycle

```
Created → Pending Review → Approved → Active → Executing
            ↓                ↓         ↓
         Rejected        Paused    Completed/Failed
```

## Viewing Job History

```python
# Get last 10 executions for a job
history = await store.get_job_history("job-id", limit=10)

for record in history:
    print(f"{record.started_at}: {record.status} ({record.duration_ms}ms)")
```

## Data Storage

Jobs are persisted to JSONL files:

| File | Purpose |
|------|---------|
| `data/cron.jsonl` | Job definitions |
| `data/cron_history.jsonl` | Execution history |
| `data/cron_logs.jsonl` | Job output logs |

## Best Practices

1. **Keep jobs idempotent** - They may run multiple times if interrupted
2. **Handle errors** - Use try/except in job code
3. **Short execution** - Jobs should complete quickly; use async for I/O
4. **Test expressions** - Verify timing before deploying

## Related Documentation

- [Job API Reference](job-api.md) — Functions available to job code
- [Notifier Architecture](notifier.md) — How notifications work
- [Architecture](ARCHITECTURE.md) — System design
