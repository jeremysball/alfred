### reject_job - Reject a Pending Job

Reject and remove a pending cron job without running it.

**Parameters:**
- `job_id` (required): The ID of the job to reject

**When to use:**
- A job has incorrect parameters
- The prompt is unclear or inappropriate
- You don't want the job to run

**Examples:**

```python
# Reject a pending job
reject_job(job_id="job-uuid-from-list")
```

**Tips:**
- Use `list_jobs()` to find pending job IDs
- Rejection is permanent - the job is deleted
- Can always create a new job with corrections
