### approve_job - Approve a Pending Job

Approve a pending cron job to start running on its schedule.

**Parameters:**
- `job_id` (required): The ID of the job to approve

**When to use:**
- After reviewing a job and confirming it's correct
- Enabling a scheduled job to run

**Examples:**

```python
# Approve a pending job
approve_job(job_id="job-uuid-from-list")
```

**Tips:**
- Use `list_jobs()` to find pending job IDs
- Review jobs with `review_job()` before approving
- Once approved, the job runs on its schedule automatically
