# PRD: Cron Job Error Handling and UX Improvements

## Overview

**Issue**: #75
**Status**: Open
**Priority**: High
**Created**: 2026-02-19

Three UX issues in the cron system degrade the user experience: unfriendly error messages, non-local timestamps, and potential CLI unresponsiveness.

---

## Problem Statement

### Issue 1: Unfriendly Job Loading Errors
When the scheduler loads a job with invalid code (missing `async def run()` function), it logs a raw Python traceback to stderr. Users see internal error messages instead of helpful guidance.

**Current behavior:**
```
ERROR:src.cron.scheduler:Failed to load job 31c03956-8fb6-4aa6-b5b7-4cc5207821e3
Traceback (most recent call last):
  File "/workspace/alfred-prd/src/cron/scheduler.py", line 276, in _load_jobs
    handler = self._compile_handler(job.code, job.sandbox_enabled)
  ...
ValueError: Job code must define an async run() function
```

**Desired behavior:**
```
WARNING: Skipping job 'EST Time Logger' - code is invalid (missing async run() function)
```

### Issue 2: Job Notifications Not in System Timezone
`CLINotifier.send()` hardcodes UTC time for notification timestamps. Users see `2026-02-19 06:48:41` when their local time is different.

**Current format:**
```
[2026-02-19 06:48:41 JOB NOTIFICATION] Hello from test job!
```

**Desired format:**
```
[2026-02-19 01:48:41 EST (06:48:41 UTC) JOB NOTIFICATION] Hello from test job!
```

### Issue 3: CLI Becomes Unresponsive
After certain job failures or errors, the CLI can stop responding to user input. The root cause requires investigation during implementation but may involve:
- Async/terminal interaction issues
- Background task exception handling
- Event loop blocking

---

## Solution Overview

### 1. Friendly Error Handling + Job Quarantine
- Catch job loading errors gracefully
- Log user-friendly messages without full tracebacks
- Mark broken jobs with `"broken"` status to prevent repeated load attempts
- Allow users to list/fix/delete broken jobs

### 2. Local Timezone Display
- Use `datetime.now().astimezone()` for local time with timezone
- Display format: `[HH:MM:SS TZ (HH:MM:SS UTC) JOB NOTIFICATION]`
- Fall back gracefully if timezone detection fails

### 3. CLI Responsiveness Fix
- Investigate and identify root cause
- Likely fixes involve:
  - Ensuring background task exceptions don't corrupt terminal state
  - Proper handling of stdout/stderr during async operations
  - Reviewing `redirect_stdout`/`redirect_stderr` interaction with CLI

---

## Technical Approach

### Error Handling Changes

**File: `src/cron/scheduler.py`**

In `_load_jobs()`:
```python
async def _load_jobs(self) -> None:
    jobs = await self._store.load_jobs()
    for job in jobs:
        if job.status == "active":
            try:
                handler = self._compile_handler(job.code, job.sandbox_enabled)
                runnable = RunnableJob.from_job(job, handler)
                self._jobs[job.job_id] = runnable
                self._job_code[job.job_id] = job.code
            except ValueError as e:
                # User-friendly error without traceback
                logger.warning(f"Skipping job '{job.name}' ({job.job_id}) - {e}")
                # Quarantine the broken job
                job.status = "broken"
                job.error_message = str(e)
                await self._store.save_job(job)
            except Exception as e:
                logger.warning(f"Skipping job '{job.name}' ({job.job_id}) - unexpected error: {e}")
                job.status = "broken"
                job.error_message = str(e)
                await self._store.save_job(job)
```

### Timezone Changes

**File: `src/cron/notifier.py`**

In `CLINotifier.send()`:
```python
async def send(self, message: str, chat_id: int | None = None) -> None:
    try:
        # Get local time with timezone
        now_local = datetime.now().astimezone()
        now_utc = datetime.now(UTC)

        # Format: "HH:MM:SS TZ (HH:MM:SS UTC)"
        local_str = now_local.strftime("%H:%M:%S") + " " + now_local.strftime("%Z")
        utc_str = now_utc.strftime("%H:%M:%S UTC")
        timestamp = f"{local_str} ({utc_str})"

        lines = message.splitlines() if message else [""]
        for i, line in enumerate(lines):
            if i == 0:
                formatted = f"[{timestamp} JOB NOTIFICATION] {line}\n"
            else:
                formatted = f"{' ' * (len(timestamp) + 22)}{line}\n"
            self.output.write(formatted)
        self.output.flush()
    except Exception as e:
        logger.error(f"Failed to send CLI notification: {e}")
```

### CLI Investigation Areas

1. **Check background task exception handling** - Ensure `asyncio.create_task()` exceptions don't corrupt state
2. **Review stdout redirection** - Verify `redirect_stdout`/`redirect_stderr` properly restore streams
3. **Test terminal state** - Ensure `input()` and `print()` work correctly after job execution

---

## Milestones

| # | Milestone | Status | Description |
|---|-----------|--------|-------------|
| M1 | Friendly error messages | ✅ Done | Catch and log user-friendly messages for invalid jobs |
| M2 | Job quarantine | ✅ Done | Mark broken jobs with `broken` status to prevent repeated failures |
| M3 | Local timezone display | ✅ Done | Display notification timestamps in local TZ with UTC fallback |
| M4 | CLI investigation | 🔲 Todo | Identify and document root cause of CLI unresponsive issue |
| M5 | CLI fix | 🔲 Todo | Implement fix for CLI unresponsive issue |
| M6 | Testing | 🔲 Todo | Add tests for error handling and timezone formatting |

---

## Success Criteria

- [x] Invalid job code shows friendly message, not Python traceback
- [x] Broken jobs are quarantined and don't repeatedly fail on scheduler restart
- [x] Notification timestamps show local timezone first, then UTC
- [ ] CLI remains responsive after job failures and errors
- [ ] All new code has test coverage

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-19 | Quarantine broken jobs instead of deleting | Allows users to inspect and fix broken code |
| 2026-02-19 | Show local TZ first with UTC in parentheses | Local time is primary, UTC as reference |
| 2026-02-19 | Use `datetime.now().astimezone()` for local TZ | Python stdlib, works on all platforms |

---

## Notes

- The `broken` status is a new job state that indicates the job has invalid code
- Users can fix broken jobs by editing the code and setting status back to `pending` for re-approval
- CLI investigation may reveal additional issues beyond what's documented here
