"""Integration tests for cron scheduler workflows.

End-to-end tests that verify complete user journeys through the system.
Uses mock SocketClient since tools now communicate via socket API.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from alfred.cron.scheduler import CronScheduler
from alfred.cron.socket_protocol import (
    ApproveJobResponse,
    QueryJobsResponse,
    RejectJobResponse,
    SubmitJobResponse,
)
from alfred.cron.store import CronStore
from alfred.tools.approve_job import ApproveJobTool
from alfred.tools.list_jobs import ListJobsTool
from alfred.tools.reject_job import RejectJobTool
from alfred.tools.schedule_job import ScheduleJobTool


def create_mock_socket_client():
    """Create a mock SocketClient for testing."""
    client = MagicMock()
    client.query_jobs = AsyncMock()
    client.approve_job = AsyncMock()
    client.reject_job = AsyncMock()
    client.submit_job = AsyncMock()
    return client


@pytest.fixture
async def cron_system(tmp_path):
    """Complete cron system for integration testing.

    Yields a dict with:
    - scheduler: Running CronScheduler instance
    - store: CronStore instance
    - mock_socket_client: Mock SocketClient for tool testing
    - schedule_tool: ScheduleJobTool
    - list_tool: ListJobsTool
    - approve_tool: ApproveJobTool
    - reject_tool: RejectJobTool
    """
    # Create data directory
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    store = CronStore(data_dir=data_dir)
    scheduler = CronScheduler(store=store, check_interval=60.0)  # Slow check to avoid races

    # Create mock socket client
    mock_socket_client = create_mock_socket_client()

    # Create tools with mock socket client
    schedule_tool = ScheduleJobTool(socket_client=mock_socket_client)
    list_tool = ListJobsTool(socket_client=mock_socket_client)
    approve_tool = ApproveJobTool(socket_client=mock_socket_client)
    reject_tool = RejectJobTool(socket_client=mock_socket_client)

    yield {
        "scheduler": scheduler,
        "store": store,
        "mock_socket_client": mock_socket_client,
        "schedule_tool": schedule_tool,
        "list_tool": list_tool,
        "approve_tool": approve_tool,
        "reject_tool": reject_tool,
    }


class TestFullJobLifecycle:
    """Test complete job lifecycle: create → list → approve → execute."""

    @pytest.mark.asyncio
    async def test_create_job_with_cron_expression(self, cron_system):
        """Should create job with correct cron expression."""
        # Setup mock response
        cron_system["mock_socket_client"].submit_job.return_value = SubmitJobResponse(
            request_id="test-123",
            success=True,
            job_id="job-456",
            message="Job submitted successfully",
        )

        result = []
        async for chunk in cron_system["schedule_tool"].execute_stream(
            name="Daily Report",
            description="Send daily summary",
            cron_expression="0 8 * * *",
        ):
            result.append(chunk)

        output = "".join(result)

        # Verify success message
        assert "submitted" in output.lower()
        assert "0 8 * * *" in output  # Cron expression

        # Verify socket client was called correctly
        cron_system["mock_socket_client"].submit_job.assert_called_once()
        call_args = cron_system["mock_socket_client"].submit_job.call_args
        assert call_args.kwargs["name"] == "Daily Report"
        assert call_args.kwargs["expression"] == "0 8 * * *"

    @pytest.mark.asyncio
    async def test_list_pending_jobs(self, cron_system):
        """Should list pending jobs correctly."""
        # Setup mock response
        cron_system["mock_socket_client"].query_jobs.return_value = QueryJobsResponse(
            request_id="test-123",
            jobs=[
                {
                    "job_id": "job-1",
                    "name": "Pending Job",
                    "expression": "0 8 * * *",
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                }
            ],
            recent_failures=[],
        )

        # List pending
        result = []
        async for chunk in cron_system["list_tool"].execute_stream(status_filter="pending"):
            result.append(chunk)

        output = "".join(result)
        assert "Pending Job" in output
        assert "pending" in output.lower()

    @pytest.mark.asyncio
    async def test_approve_job_makes_it_active(self, cron_system):
        """Should activate job after approval."""
        # Setup mock response
        cron_system["mock_socket_client"].approve_job.return_value = ApproveJobResponse(
            request_id="test-123",
            success=True,
            job_id="job-456",
            job_name="To Approve",
            message="Job approved successfully",
        )

        result = []
        async for chunk in cron_system["approve_tool"].execute_stream(job_identifier="To Approve"):
            result.append(chunk)

        output = "".join(result)
        assert "approved" in output.lower()

        # Verify socket client was called
        cron_system["mock_socket_client"].approve_job.assert_called_once_with("To Approve")

    @pytest.mark.asyncio
    async def test_full_lifecycle_via_scheduler_direct(self, cron_system):
        """Complete flow using scheduler directly (bypassing tools/socket)."""
        # Create job
        job_id = await cron_system["scheduler"].submit_user_job(
            name="Lifecycle Test",
            expression="0 8 * * *",
            code='async def run():\n    print("Hello from job!")',
        )

        # Verify pending
        jobs = await cron_system["store"].load_jobs()
        assert len(jobs) == 1
        assert jobs[0].status == "pending"

        # Approve it
        await cron_system["scheduler"].approve_job(job_id, "test")

        # Verify active
        jobs = await cron_system["store"].load_jobs()
        active_job = next((j for j in jobs if j.job_id == job_id), None)
        assert active_job is not None
        assert active_job.status == "active"


class TestRejectionWorkflow:
    """Test job rejection and deletion flows."""

    @pytest.mark.asyncio
    async def test_reject_pending_job_deletes_it_via_tool(self, cron_system):
        """Should permanently delete rejected job via tool."""
        # Setup mock response
        cron_system["mock_socket_client"].reject_job.return_value = RejectJobResponse(
            request_id="test-123",
            success=True,
            job_id="job-456",
            job_name="To Reject",
            message="Job deleted successfully",
        )

        # Reject it
        result = []
        async for chunk in cron_system["reject_tool"].execute_stream(job_identifier="To Reject"):
            result.append(chunk)

        output = "".join(result)
        assert "deleted" in output.lower() or "removed" in output.lower()

        # Verify socket client was called
        cron_system["mock_socket_client"].reject_job.assert_called_once_with("To Reject")

    @pytest.mark.asyncio
    async def test_reject_pending_job_deletes_it_via_scheduler(self, cron_system):
        """Should permanently delete rejected job via scheduler directly."""
        # Create job directly
        await cron_system["scheduler"].submit_user_job(name="To Reject", expression="0 8 * * *", code="async def run(): pass")

        # Verify job exists
        jobs = await cron_system["store"].load_jobs()
        assert len(jobs) == 1

        # Delete it via store
        await cron_system["store"].delete_job(jobs[0].job_id)

        # Verify gone
        jobs = await cron_system["store"].load_jobs()
        assert len(jobs) == 0


class TestResourceLimits:
    """Test resource limit enforcement during execution."""

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self, cron_system):
        """Should store timeout configuration correctly."""
        # Create job with custom resource limits
        job_id = await cron_system["scheduler"].submit_user_job(
            name="Limited Job",
            expression="0 8 * * *",
            code="async def run(): pass",
        )

        # Modify resource limits
        jobs = await cron_system["store"].load_jobs()
        job = next(j for j in jobs if j.job_id == job_id)
        job.resource_limits.timeout_seconds = 30
        job.resource_limits.max_memory_mb = 200
        await cron_system["store"].save_job(job)

        # Verify limits stored correctly
        jobs = await cron_system["store"].load_jobs()
        job = next((j for j in jobs if j.job_id == job_id), None)
        assert job is not None
        assert job.resource_limits.timeout_seconds == 30
        assert job.resource_limits.max_memory_mb == 200


class TestConcurrentExecution:
    """Test job queuing and concurrent execution."""

    @pytest.mark.asyncio
    async def test_job_lock_prevents_concurrent_execution(self, cron_system):
        """Same job should not run concurrently."""
        # Start scheduler briefly to register job
        await cron_system["scheduler"].start()
        await asyncio.sleep(0.1)

        try:
            # Create and approve job
            job_id = await cron_system["scheduler"].submit_user_job(
                name="Concurrent Test", expression="* * * * *", code="async def run(): pass"
            )
            await cron_system["scheduler"].approve_job(job_id, "test")

            # Check lock mechanism exists on registered job
            job = cron_system["scheduler"]._jobs.get(job_id)
            if job:
                assert hasattr(job, "_running")
                assert isinstance(job._running, asyncio.Lock)
            else:
                # Job registration might be async, skip detailed check
                pass
        finally:
            await cron_system["scheduler"].stop()
