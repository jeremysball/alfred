"""RejectJobTool - Reject or delete pending cron jobs.

Tool for Alfred to reject and remove jobs awaiting approval.
"""

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.cron.scheduler import CronScheduler
from src.tools.base import Tool, ToolResult


class RejectJobParams(BaseModel):
    """Parameters for rejecting a cron job."""

    job_identifier: str = Field(
        description="Job name or ID to reject/delete (e.g., 'Daily Report' or job ID)",
        min_length=1,
    )

    @field_validator("job_identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Ensure identifier is not whitespace-only."""
        if not v.strip():
            raise ValueError("Job identifier cannot be empty")
        return v.strip()


class RejectJobResult(ToolResult):
    """Result from rejecting a job."""

    job_id: str | None = Field(default=None, description="ID of rejected job")
    job_name: str | None = Field(default=None, description="Name of rejected job")


class RejectJobTool(Tool):
    """Reject and delete a pending cron job.

    The job will be permanently removed from the system.

    Examples:
    - "Reject the daily report job" -> job_identifier="Daily Report"
    - "Delete job abc-123" -> job_identifier="abc-123"
    - "Cancel my weekly reminder" -> job_identifier="weekly reminder"
    """

    name = "reject_job"
    description = (
        "Reject and delete a pending cron job. "
        "The job will be permanently removed from the system."
    )
    param_model = RejectJobParams

    def __init__(self, scheduler: CronScheduler) -> None:
        """Initialize with CronScheduler instance."""
        super().__init__()
        self.scheduler = scheduler

    def execute(self, **kwargs: Any) -> str:
        """Execute the reject_job tool (sync - not supported)."""
        return "Error: RejectJobTool must be called via execute_stream in async context"

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Execute the reject_job tool (async)."""
        try:
            params = RejectJobParams(**kwargs)
        except ValueError as e:
            yield f"Error: Invalid parameters - {e}"
            return

        identifier = params.job_identifier

        try:
            # Load all jobs
            jobs = await self.scheduler._store.load_jobs()

            # Find job by ID or name
            job = self._find_job(jobs, identifier)

            if job is None:
                yield (
                    f"Couldn't find a job matching '{identifier}'.\n\n"
                    f"Use 'list_jobs' to see available jobs."
                )
                return

            # Confirm deletion
            await self.scheduler._store.delete_job(job.job_id)

            result = RejectJobResult(
                success=True,
                message=f"✓ Deleted '{job.name}'. The job has been removed.",
                job_id=job.job_id,
                job_name=job.name,
            )
            yield result.message

        except Exception as e:
            yield f"Error: Failed to reject job - {e}"

    def _find_job(self, jobs: list, identifier: str) -> Any | None:
        """Find job by ID or fuzzy name match."""
        identifier_lower = identifier.lower()

        # Try exact ID match first
        for job in jobs:
            if job.job_id == identifier:
                return job

        # Try exact name match
        for job in jobs:
            if job.name.lower() == identifier_lower:
                return job

        # Try substring name match (must be unique)
        matches = [j for j in jobs if identifier_lower in j.name.lower()]
        if len(matches) == 1:
            return matches[0]

        return None
