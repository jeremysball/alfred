"""ApproveJobTool - Approve pending cron jobs.

Tool for Alfred to approve jobs awaiting approval.
"""

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.cron.scheduler import CronScheduler
from src.tools.base import Tool, ToolResult


class ApproveJobParams(BaseModel):
    """Parameters for approving a cron job."""

    job_identifier: str = Field(
        description="Job name or ID to approve (e.g., 'Daily Report' or job ID)",
        min_length=1,
    )

    @field_validator("job_identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Ensure identifier is not whitespace-only."""
        if not v.strip():
            raise ValueError("Job identifier cannot be empty")
        return v.strip()


class ApproveJobResult(ToolResult):
    """Result from approving a job."""

    message: str = Field(default="", description="Human-readable result message")
    job_id: str | None = Field(default=None, description="ID of approved job")
    job_name: str | None = Field(default=None, description="Name of approved job")


class ApproveJobTool(Tool):
    """Approve a pending cron job.

    The job will be activated and start running on its schedule.

    Examples:
    - "Approve the daily report job" -> job_identifier="Daily Report"
    - "Approve job abc-123" -> job_identifier="abc-123"
    """

    name = "approve_job"
    description = (
        "Approve a pending cron job. The job will be activated and start running on its schedule."
    )
    param_model = ApproveJobParams

    def __init__(self, scheduler: CronScheduler) -> None:
        """Initialize with CronScheduler instance.

        Args:
            scheduler: The cron scheduler to approve jobs through
        """
        super().__init__()
        self.scheduler = scheduler

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Execute the approve_job tool (async).

        Args:
            **kwargs: Tool parameters matching ApproveJobParams

        Yields:
            Result message
        """
        try:
            params = ApproveJobParams(**kwargs)
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

            # Check if already active
            if job.status == "active":
                yield f"✓ Job '{job.name}' is already active and running."
                return

            # Check if not pending
            if job.status != "pending":
                yield (
                    f"Cannot approve job '{job.name}' - it's currently {job.status} (not pending)."
                )
                return

            # Approve the job
            result = await self.scheduler.approve_job(job.job_id, "user")

            if result["success"]:
                base_msg = result["message"]
                full_message = f"✓ {base_msg}. The job is now active and will run on schedule."
                approve_result = ApproveJobResult(
                    success=True,
                    message=full_message,
                    job_id=job.job_id,
                    job_name=job.name,
                )
                yield approve_result.message
            else:
                yield f"Error: {result['message']}"

        except Exception as e:
            yield f"Error: Failed to approve job - {e}"

    def _find_job(self, jobs: list, identifier: str) -> Any | None:
        """Find job by ID or fuzzy name match.

        Args:
            jobs: List of jobs to search
            identifier: Job ID or name to match

        Returns:
            Matching job or None
        """
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

        # Try partial word match
        if len(matches) > 1:
            # Too many matches - return None to indicate ambiguity
            return None

        return None
