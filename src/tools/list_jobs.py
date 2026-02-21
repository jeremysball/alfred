"""ListJobsTool - List cron jobs with filtering.

Tool for Alfred to list jobs by status (pending, active, all).
"""

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, Field

from src.cron.scheduler import CronScheduler
from src.tools.base import Tool, ToolResult


class ListJobsParams(BaseModel):
    """Parameters for listing cron jobs."""

    status_filter: str = Field(
        default="all",
        description="Filter by status: 'all', 'pending', 'active', 'paused'",
    )


class ListJobsResult(ToolResult):
    """Result from listing jobs."""

    jobs: list[dict] = Field(default_factory=list, description="List of job details")
    total_count: int = Field(default=0, description="Total number of jobs")


class ListJobsTool(Tool):
    """List cron jobs with optional status filtering.

    Examples:
    - "Show me my pending jobs" -> status_filter="pending"
    - "What jobs do I have?" -> status_filter="all"
    - "List active jobs" -> status_filter="active"
    """

    name = "list_jobs"
    description = (
        "List cron jobs with optional filtering by status. "
        "Use to show pending jobs awaiting approval or all active jobs."
    )
    param_model = ListJobsParams

    def __init__(self, scheduler: CronScheduler) -> None:
        """Initialize with CronScheduler instance.

        Args:
            scheduler: The cron scheduler to query for jobs
        """
        super().__init__()
        self.scheduler = scheduler

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Execute the list_jobs tool (async).

        Args:
            **kwargs: Tool parameters matching ListJobsParams

        Yields:
            Formatted list of jobs
        """
        try:
            params = ListJobsParams(**kwargs)
        except ValueError as e:
            yield f"Error: Invalid parameters - {e}"
            return

        # Normalize filter
        status_filter = params.status_filter.lower().strip()
        valid_filters = ["all", "pending", "active", "paused"]

        if status_filter not in valid_filters:
            yield (
                f"Error: Invalid status filter '{status_filter}'. "
                f"Use one of: {', '.join(valid_filters)}"
            )
            return

        try:
            # Load jobs from store
            jobs = await self.scheduler._store.load_jobs()

            # Filter by status
            if status_filter != "all":
                jobs = [j for j in jobs if j.status == status_filter]

            if not jobs:
                if status_filter == "all":
                    yield "You don't have any jobs scheduled."
                else:
                    yield f"No {status_filter} jobs found."
                return

            # Format output
            lines = []
            if status_filter == "all":
                lines.append(f"You have {len(jobs)} job(s):\n")
            else:
                lines.append(f"Found {len(jobs)} {status_filter} job(s):\n")

            for i, job in enumerate(jobs, 1):
                status_emoji = {
                    "pending": "⏳",
                    "active": "✅",
                    "paused": "⏸️",
                }.get(job.status, "❓")

                lines.append(f"{i}. {status_emoji} {job.name}")
                lines.append(f"   Status: {job.status}")
                lines.append(f"   Schedule: {job.expression}")
                if job.last_run:
                    lines.append(f"   Last run: {job.last_run.strftime('%Y-%m-%d %H:%M')}")
                lines.append(f"   ID: {job.job_id[:8]}...")
                lines.append("")

            yield "\n".join(lines)

        except Exception as e:
            yield f"Error: Failed to list jobs - {e}"
