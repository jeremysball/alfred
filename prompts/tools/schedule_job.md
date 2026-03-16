### schedule_job - Schedule a Recurring Task

Schedule a recurring task (cron job) to run at specified intervals.

**Parameters:**
- `name` (required): A descriptive name for the job
- `schedule` (required): Cron expression or natural language (e.g., "every day at 9am")
- `prompt` (required): The prompt/instruction to execute
- `time_zone` (optional): Time zone (default: America/New_York)

**When to use:**
- Setting up daily/weekly reports
- Scheduling recurring reminders
- Automating periodic tasks
- Background monitoring jobs

**Examples:**

```python
# Daily standup reminder
schedule_job(
    name="Daily Standup",
    schedule="every weekday at 9:30am",
    prompt="Generate a summary of yesterday's commits and today's plan"
)

# Weekly review
schedule_job(
    name="Weekly Review",
    schedule="every Friday at 4pm",
    prompt="Review open PRs and provide status update"
)

# Cron expression format
schedule_job(
    name="Hourly Check",
    schedule="0 * * * *",
    prompt="Check system status and report any issues"
)
```

**Tips:**
- Natural language: "every day at 9am", "every Monday at 10am"
- Cron format: "0 9 * * 1-5" (weekdays at 9am)
- The prompt is what gets executed when the job runs
- Jobs run in the background and can send notifications
