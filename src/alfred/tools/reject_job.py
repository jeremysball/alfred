"""RejectJobTool - Reject or delete pending cron jobs.

Tool for Alfred to reject and remove jobs awaiting approval.
Uses SocketClient to reject jobs via the daemon socket API.
"""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from alfred.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from alfred.cron.socket_client import SocketClient


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

    message: str = Field(default="", description="Human-readable result message")
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
        "Reject and delete a pending cron job. The job will be permanently removed from the system."
    )
    param_model = RejectJobParams

    def __init__(self, socket_client: "SocketClient") -> None:
        """Initialize with SocketClient instance."""
        super().__init__()
        self.socket_client = socket_client

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Execute the reject_job tool (async)."""
        try:
            params = RejectJobParams(**kwargs)
        except ValueError as e:
            yield f"Error: Invalid parameters - {e}"
            return

        identifier = params.job_identifier

        try:
            # Reject job via socket API
            response = await self.socket_client.reject_job(identifier)

            if response is None:
                yield (
                    f"Error: Failed to reject job '{identifier}'.\n\n"
                    f"The cron daemon may not be running. "
                    f"Use 'alfred daemon status' to check."
                )
                return

            if response.success:
                result = RejectJobResult(
                    success=True,
                    message=f"✓ Deleted '{response.job_name}'. The job has been removed.",
                    job_id=response.job_id,
                    job_name=response.job_name,
                )
                yield result.message
            else:
                yield f"Error: {response.message}"

        except Exception as e:
            yield f"Error: Failed to reject job - {e}"
