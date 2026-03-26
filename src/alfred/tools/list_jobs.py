"""ListJobsTool - List cron jobs with filtering.

Tool for Alfred to list jobs by status (pending, active, all).
Uses SocketClient to query jobs via the daemon socket API.
"""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from alfred.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from alfred.cron.socket_client import SocketClient


class ListJobsParams(BaseModel):
    """Parameters for listing cron jobs."""

    status_filter: str = Field(
        default="all",
        description="Filter by status: 'all', 'pending', 'active', 'paused'",
    )


class ListJobsResult(ToolResult):
    """Result from listing jobs."""

    jobs: list[dict[str, Any]] = Field(default_factory=list, description="List of job details")
    total_count: int = Field(default=0, description="Total number of jobs")


class ListJobsTool(Tool):
    """List cron jobs with optional status filtering.

    Examples:
    - "Show me my pending jobs" -> status_filter="pending"
    - "What jobs do I have?" -> status_filter="all"
    - "List active jobs" -> status_filter="active"
    """

    name = "list_jobs"
    description = "List cron jobs with optional filtering by status. Use to show pending jobs awaiting approval or all active jobs."
    param_model = ListJobsParams

    def __init__(self, socket_client: "SocketClient | None" = None, data_dir: Any = None) -> None:
        """Initialize with SocketClient instance or data_dir for fallback.

        Args:
            socket_client: The socket client to query jobs through (optional)
            data_dir: Directory for direct store access fallback (optional)
        """
        super().__init__()
        self.socket_client = socket_client
        self.data_dir = data_dir

    async def _get_jobs_via_socket(self, status_filter: str) -> list[dict[str, Any]] | None:
        """Try to get jobs via socket API."""
        if not self.socket_client:
            return None

        try:
            # Ensure socket client is started
            if not self.socket_client.is_connected:
                await self.socket_client.start()

            if not self.socket_client.is_connected:
                return None

            response = await self.socket_client.query_jobs()
            if response is None:
                return None

            jobs = response.jobs
            if status_filter != "all":
                jobs = [j for j in jobs if j.get("status") == status_filter]
            return jobs
        except Exception:
            return None

    async def _get_jobs_via_store(self, status_filter: str) -> list[dict[str, Any]] | None:
        """Fallback: get jobs directly from store."""
        try:
            from alfred.cron.store import CronStore
            from alfred.data_manager import get_data_dir

            data_dir = self.data_dir or get_data_dir()
            store = CronStore(data_dir)
            jobs = await store.load_jobs()

            result = []
            for job in jobs:
                job_dict = {
                    "job_id": job.job_id,
                    "name": job.name,
                    "status": job.status,
                    "expression": job.expression,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                }
                result.append(job_dict)

            if status_filter != "all":
                result = [j for j in result if j.get("status") == status_filter]
            return result
        except Exception:
            return None

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
            yield (f"Error: Invalid status filter '{status_filter}'. Use one of: {', '.join(valid_filters)}")
            return

        # Try socket first, then fallback to direct store access
        jobs = await self._get_jobs_via_socket(status_filter)
        if jobs is None:
            jobs = await self._get_jobs_via_store(status_filter)

        if jobs is None:
            yield "Error: Failed to query jobs - daemon may not be running"
            return

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
            status = job.get("status", "unknown")
            status_emoji = {
                "pending": "⏳",
                "active": "✅",
                "paused": "⏸️",
            }.get(status, "❓")

            lines.append(f"{i}. {status_emoji} {job.get('name', 'Unnamed')}")
            lines.append(f"   Status: {status}")
            lines.append(f"   Schedule: {job.get('expression', 'N/A')}")

            # Handle last_run formatting
            last_run = job.get("last_run")
            if last_run:
                if isinstance(last_run, str):
                    lines.append(f"   Last run: {last_run}")
                else:
                    lines.append(f"   Last run: {last_run.strftime('%Y-%m-%d %H:%M')}")

            job_id = job.get("job_id", "")
            lines.append(f"   ID: {job_id[:8]}..." if job_id else "   ID: N/A")
            lines.append("")

        yield "\n".join(lines)
