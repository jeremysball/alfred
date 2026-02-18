"""ScheduleJobTool - Create recurring cron jobs.

Tool for Alfred to schedule tasks via natural language.
"""


from pydantic import BaseModel, Field, field_validator

from src.cron import parser
from src.cron.scheduler import CronScheduler
from src.tools.base import Tool, ToolResult


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
        description=("When to run the job. Examples: '0 9 * * *' (9am daily), "
                     "'*/5 * * * *' (every 5 min)"),
    )
    code: str | None = Field(
        default=None,
        description=("Optional Python code. If not provided, code will be "
                     "generated from description"),
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


class ScheduleJobTool(Tool):
    """Create a recurring cron job that runs on a schedule.

    The job will be created with "pending" status and require human approval
    before it starts running. This ensures safety for automated job creation.

    Example usage:
    - "Schedule a daily report at 9am" -> name="Daily Report", cron="0 9 * * *"
    - "Remind me every hour" -> name="Hourly Reminder", cron="0 * * * *"
    """

    name = "schedule_job"
    description = (
        "Create a recurring cron job that runs on a schedule. "
        "The job will be created with 'pending' status and require approval before running."
    )
    param_model = ScheduleJobParams

    def __init__(self, scheduler: CronScheduler) -> None:
        """Initialize with CronScheduler instance.

        Args:
            scheduler: The cron scheduler to submit jobs to
        """
        self.scheduler = scheduler

    async def execute(self, params: ScheduleJobParams) -> ToolResult:
        """Execute the schedule_job tool.

        Args:
            params: Tool parameters

        Returns:
            ToolResult with job ID or error message
        """
        # Validate cron expression
        if not parser.is_valid(params.cron_expression):
            return ToolResult(
                error=f"Invalid cron expression: '{params.cron_expression}'. "
                      f"Use standard 5-field format like '0 9 * * *' for 9am daily."
            )

        # Generate or use provided code
        job_code = params.code or self._generate_code(params.description)

        try:
            # Validate generated/provided code compiles
            compile(job_code, "<string>", "exec")
        except SyntaxError as e:
            return ToolResult(
                error=f"Invalid Python code: {e}"
            )

        try:
            # Submit job for approval
            job_id = await self.scheduler.submit_user_job(
                name=params.name,
                expression=params.cron_expression,
                code=job_code,
            )

            return ToolResult(
                output=(
                    f"Job '{params.name}' submitted for approval. "
                    f"Job ID: {job_id}\n"
                    f"To approve and activate: /cron approve {job_id}\n"
                    f"To view details: /cron review {job_id}"
                )
            )

        except Exception as e:
            return ToolResult(
                error=f"Failed to create job: {e}"
            )

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
    # TODO: Implement the job logic
    # This is an auto-generated placeholder
    # Description: {safe_description}

    # Example: Send notification, log to file, etc.
    # Replace with actual implementation
    print(f"Executing job: {safe_description}")

    # Placeholder for actual work
    # Common patterns:
    # - await notify("Message")  # Send notification
    # - await remember("Text")   # Save to memory
    # - await search("Query")    # Search memories
    # - Custom HTTP requests, file operations, etc.
    pass
'''
