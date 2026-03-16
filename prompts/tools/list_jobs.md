### list_jobs - List Scheduled Jobs

View all scheduled cron jobs and their status.

**Parameters:**
- No parameters required

**When to use:**
- Checking what jobs are scheduled
- Reviewing job status
- Finding job IDs for approval/rejection

**Examples:**

```python
# List all scheduled jobs
list_jobs()
```

**Tips:**
- Shows job name, schedule, status, and last run time
- Status can be: pending, running, completed, failed
- Jobs in "pending" status may need approval
