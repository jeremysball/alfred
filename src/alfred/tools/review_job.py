"""ReviewJobTool - Review cron job details including code.

Tool for Alfred to review job details and see the code before approving.
Uses SocketClient to query jobs via the daemon socket API.
"""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from alfred.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from alfred.cron.socket_client import SocketClient


class ReviewJobParams(BaseModel):
    """Parameters for reviewing a cron job."""

    job_identifier: str = Field(
        description="Job name or ID to review (e.g., 'Daily Report' or job ID)",
        min_length=1,
    )

    @field_validator("job_identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Ensure identifier is not whitespace-only."""
        if not v.strip():
            raise ValueError("Job identifier cannot be empty")
        return v.strip()


class ReviewJobResult(ToolResult):
    """Result from reviewing a job."""

    job_id: str | None = Field(default=None, description="ID of the job")
    job_name: str | None = Field(default=None, description="Name of the job")
    status: str | None = Field(default=None, description="Current status")
    expression: str | None = Field(default=None, description="Cron expression")
    code: str | None = Field(default=None, description="Python code for the job")


class ReviewJobTool(Tool):
    """Review a cron job's details including its code.

    Use this before approving a job to see what code will be executed.

    Examples:
    - "Show me the daily report job" -> job_identifier="Daily Report"
    - "Review job abc-123" -> job_identifier="abc-123"
    """

    name = "review_job"
    description = (
        "Review a cron job's details including its Python code. "
        "Use before approving to see what code will be executed."
    )
    param_model = ReviewJobParams

    def __init__(self, socket_client: "SocketClient") -> None:
        """Initialize with SocketClient instance.

        Args:
            socket_client: The socket client to query jobs through
        """
        super().__init__()
        self.socket_client = socket_client

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Execute the review_job tool (async).

        Args:
            **kwargs: Tool parameters matching ReviewJobParams

        Yields:
            Job details including code
        """
        try:
            params = ReviewJobParams(**kwargs)
        except ValueError as e:
            yield f"Error: Invalid parameters - {e}"
            return

        identifier = params.job_identifier

        try:
            # Query jobs via socket API
            response = await self.socket_client.query_jobs()

            if response is None:
                yield (
                    "Error: Failed to query jobs.\n\n"
                    "The cron daemon may not be running. "
                    "Use 'alfred daemon status' to check."
                )
                return

            # Find job by ID or name
            job = self._find_job(response.jobs, identifier)

            if job is None:
                yield f"Error: Job '{identifier}' not found."
                return

            # Format job details
            lines = []
            lines.append(f"Job: {job.get('name', 'Unnamed')}")
            lines.append(f"ID: {job.get('job_id', 'N/A')}")
            lines.append(f"Status: {job.get('status', 'unknown')}")
            lines.append(f"Schedule: {job.get('expression', 'N/A')}")
            lines.append("")
            lines.append("Python Code:")
            lines.append("```python")
            code = job.get("code", "# No code available")
            lines.append(code)
            lines.append("```")

            if job.get("status") == "pending":
                lines.append("")
                lines.append("This job is pending approval.")
                lines.append(f"To approve: use approve_job with identifier '{identifier}'")

            yield "\n".join(lines)

        except Exception as e:
            yield f"Error: Failed to review job - {e}"

    def _find_job(self, jobs: list[dict[str, Any]], identifier: str) -> dict[str, Any] | None:
        """Find job by ID or fuzzy name match.

        Args:
            jobs: List of job dictionaries
            identifier: Job ID or name to search for

        Returns:
            Job dict if found, None otherwise
        """
        identifier_lower = identifier.lower()

        # Try exact ID match first
        for job in jobs:
            if job.get("job_id") == identifier:
                return job

        # Try partial ID match
        for job in jobs:
            job_id = job.get("job_id", "")
            if job_id.startswith(identifier):
                return job

        # Try exact name match
        for job in jobs:
            if job.get("name", "").lower() == identifier_lower:
                return job

        # Try substring name match (must be unique)
        matches = [j for j in jobs if identifier_lower in j.get("name", "").lower()]
        if len(matches) == 1:
            return matches[0]

        return None
