"""ScheduleJobTool - Create recurring cron jobs.

Tool for Alfred to schedule tasks via natural language.
Uses SocketClient to submit jobs via the daemon socket API.
"""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from alfred.cron import parser
from alfred.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from alfred.config import Config
    from alfred.cron.socket_client import SocketClient


class ScheduleJobParams(BaseModel):
    """Parameters for scheduling a cron job."""

    name: str = Field(
        description="Human-readable name for the job",
        min_length=1,
        max_length=100,
    )
    description: str = Field(
        description="What the job should do (used to generate code if not provided)",
        min_length=1,
        max_length=500,
    )
    cron_expression: str = Field(
        description=(
            "When to run the job. Use cron format: '0 9 * * *' for 9am daily, "
            "'*/15 * * * *' for every 15 minutes, '0 19 * * 0' for Sundays at 7pm"
        ),
    )
    code: str | None = Field(
        default=None,
        description=("Optional Python code. If not provided, code will be generated from description"),
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not whitespace-only."""
        if not v.strip():
            raise ValueError("Job name cannot be empty or whitespace")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Ensure description is not whitespace-only."""
        if not v.strip():
            raise ValueError("Description cannot be empty or whitespace")
        return v.strip()


class ScheduleJobResult(ToolResult):
    """Result from scheduling a job."""

    job_id: str | None = Field(
        default=None,
        description="ID of the created job (if successful)",
    )
    message: str = Field(
        default="",
        description="Human-readable result message",
    )


class ScheduleJobTool(Tool):
    """Create a recurring cron job that runs on a schedule.

    The job will be created with "pending" status and require human approval
    before it starts running. This ensures safety for automated job creation.

    Use standard cron format:
    - "0 9 * * *" for 9am daily
    - "*/15 * * * *" for every 15 minutes
    - "0 19 * * 0" for Sundays at 7pm
    - "0 9 * * 1-5" for weekdays at 9am
    """

    name = "schedule_job"
    description = (
        "Create a recurring cron job that runs on a schedule. "
        "The job will be created with 'pending' status and require approval before running."
    )
    param_model = ScheduleJobParams

    def __init__(self, socket_client: "SocketClient", config: "Config | None" = None) -> None:
        """Initialize with SocketClient instance.

        Args:
            socket_client: The socket client to submit jobs through
            config: Optional configuration
        """
        super().__init__()
        self.socket_client = socket_client
        self._config = config

    async def execute_stream(self, **kwargs: Any) -> AsyncIterator[str]:
        """Execute the schedule_job tool (async).

        Args:
            **kwargs: Tool parameters matching ScheduleJobParams

        Yields:
            Result message with job details or error
        """
        try:
            params = ScheduleJobParams(**kwargs)
        except ValueError as e:
            yield f"Error: Invalid parameters - {e}"
            return

        # Validate cron expression
        if not parser.is_valid(params.cron_expression):
            yield (
                f"Error: Invalid cron expression '{params.cron_expression}'.\n\n"
                f"Use cron format:\n"
                f"- '0 9 * * *' for 9am daily\n"
                f"- '*/15 * * * *' for every 15 minutes\n"
                f"- '0 19 * * 0' for Sundays at 7pm\n"
                f"- '0 9 * * 1-5' for weekdays at 9am"
            )
            return

        cron_expression = params.cron_expression

        # Generate or use provided code
        job_code = params.code or self._generate_code(params.description)

        try:
            # Validate generated/provided code compiles
            compile(job_code, "<string>", "exec")
        except SyntaxError as e:
            yield f"Error: Invalid Python code - {e}"
            return

        try:
            # Submit job via socket API
            response = await self.socket_client.submit_job(
                name=params.name,
                expression=cron_expression,
                code=job_code,
            )

            if response is None:
                yield (
                    f"Error: Failed to submit job '{params.name}'.\n\n"
                    f"The cron daemon may not be running. "
                    f"Use 'alfred daemon status' to check."
                )
                return

            if response.success:
                result = ScheduleJobResult(
                    success=True,
                    message=(
                        f"✓ Job '{params.name}' submitted for approval.\n\n"
                        f"Cron: {cron_expression}\n"
                        f"Job ID: {response.job_id}\n\n"
                        f"This job requires approval before it will run."
                    ),
                    job_id=response.job_id,
                )
                yield result.message
            else:
                yield f"Error: {response.message}"

        except Exception as e:
            yield f"Error: Failed to create job - {e}"

    def _generate_code(self, description: str) -> str:
        """Generate Python code from natural language description.

        This is a simple template-based generation. Future versions could
        use LLM to generate more sophisticated code.

        Args:
            description: What the job should do

        Returns:
            Python code as string
        """
        # Escape quotes in description for docstring
        safe_description = description.replace('"', '"').replace("'", "'")

        return f'''"""{safe_description}"""

async def run():
    """{safe_description}"""
    # ALL code goes inside async def run()
    # notify is injected automatically - do NOT import it

    # Example: Send notification
    await notify("Job started: {safe_description}")

    # Your job logic here
    print(f"Executing job: {safe_description}")

    # Example: Import libraries inside run()
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     response = await client.get("https://api.example.com")
    #     print(response.status_code)

    await notify("Job completed: {safe_description}")
'''
