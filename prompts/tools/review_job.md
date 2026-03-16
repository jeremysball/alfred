### review_job - Review a Pending Job

Review the details of a pending cron job before deciding to approve or reject it.

**Parameters:**
- `job_id` (required): The ID of the job to review

**When to use:**
- Examining a job before approval
- Understanding what a job will do
- Checking the prompt and schedule details

**Examples:**

```python
# Review a specific job
review_job(job_id="job-uuid-from-list")
```

**Tips:**
- Use `list_jobs()` first to find pending job IDs
- Shows the full prompt that will be executed
- Review carefully before approving
- Jobs can be rejected if the prompt is unclear or incorrect
