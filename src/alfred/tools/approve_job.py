"""ApproveJobTool - Approve pending cron jobs.

Tool for Alfred to approve jobs awaiting approval.
Uses SocketClient to approve jobs via the daemon socket API.
"""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from alfred.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from alfred.cron.socket_client import SocketClient


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

    def __init__(self, socket_client: "SocketClient") -> None:
        """Initialize with SocketClient instance.

        Args:
            socket_client: The socket client to approve jobs through
        """
        super().__init__()
        self.socket_client = socket_client

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
            # Approve job via socket API
            response = await self.socket_client.approve_job(identifier)

            if response is None:
                yield (
                    f"Error: Failed to approve job '{identifier}'.\n\n"
                    f"The cron daemon may not be running. "
                    f"Use 'alfred daemon status' to check."
                )
                return

            if response.success:
                yield (
                    f"✓ {response.message}.\n\n"
                    f"Job '{response.job_name}' is now active and will run on schedule."
                )
            else:
                yield f"Error: {response.message}"

        except Exception as e:
            yield f"Error: Failed to approve job - {e}"
