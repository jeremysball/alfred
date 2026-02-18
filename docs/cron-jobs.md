# Cron Jobs Documentation

## Overview

Alfred's cron system allows scheduling recurring tasks. Jobs run in the background at specified intervals using standard cron syntax.

## Creating a Job

Jobs are defined with Python code and a cron expression.

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
- `remember(text)` - Save to long-term memory
- `search(query)` - Search memories
- `store_get(key)` - Get value from key-value store
- `store_set(key, value)` - Set value in key-value store

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

## Best Practices

1. **Keep jobs idempotent** - They may run multiple times if interrupted
2. **Handle errors** - Use try/except in job code
3. **Short execution** - Jobs should complete quickly; use async for I/O
4. **Test expressions** - Use `get_next_run()` to verify timing

## CLI Commands

```bash
# List all jobs
alfred cron list

# Submit new job (pending approval)
alfred cron submit "My Job" "*/5 * * * *" "async def run(): pass"

# Approve pending job
alfred cron approve <job-id>

# View job history
alfred cron history <job-id>
```
