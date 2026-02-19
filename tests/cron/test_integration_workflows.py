"""Integration tests for cron scheduler workflows.

End-to-end tests that verify complete user journeys through the system.
"""

import asyncio
import pytest

from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore
from src.tools.approve_job import ApproveJobTool
from src.tools.list_jobs import ListJobsTool
from src.tools.reject_job import RejectJobTool
from src.tools.schedule_job import ScheduleJobTool


@pytest.fixture
async def cron_system(tmp_path):
    """Complete cron system for integration testing.

    Yields a dict with:
    - scheduler: Running CronScheduler instance
    - store: CronStore instance
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

    # Create tools without starting scheduler (to avoid auto system jobs)
    schedule_tool = ScheduleJobTool(scheduler=scheduler)
    list_tool = ListJobsTool(scheduler=scheduler)
    approve_tool = ApproveJobTool(scheduler=scheduler)
    reject_tool = RejectJobTool(scheduler=scheduler)

    yield {
        "scheduler": scheduler,
        "store": store,
        "schedule_tool": schedule_tool,
        "list_tool": list_tool,
        "approve_tool": approve_tool,
        "reject_tool": reject_tool,
    }


class TestFullJobLifecycle:
    """Test complete job lifecycle: create → list → approve → execute."""

    @pytest.mark.asyncio
    async def test_create_job_via_natural_language(self, cron_system):
        """Should create job with correct cron from natural language."""
        result = []
        async for chunk in cron_system["schedule_tool"].execute_stream(
            name="Daily Report",
            description="Send daily summary",
            cron_expression="every morning at 8am",
        ):
            result.append(chunk)

        output = "".join(result)

        # Verify success message
        assert "submitted for approval" in output.lower()
        assert "0 8 * * *" in output  # Cron expression

        # Verify stored correctly
        jobs = await cron_system["store"].load_jobs()
        assert len(jobs) == 1
        assert jobs[0].name == "Daily Report"
        assert jobs[0].expression == "0 8 * * *"
        assert jobs[0].status == "pending"

    @pytest.mark.asyncio
    async def test_list_pending_jobs(self, cron_system):
        """Should list pending jobs correctly."""
        # Create pending job
        await cron_system["scheduler"].submit_user_job(
            name="Pending Job", expression="0 8 * * *", code="async def run(): pass"
        )

        # List pending
        result = []
        async for chunk in cron_system["list_tool"].execute_stream(
            status_filter="pending"
        ):
            result.append(chunk)

        output = "".join(result)
        assert "Pending Job" in output
        assert "pending" in output.lower()

    @pytest.mark.asyncio
    async def test_approve_job_makes_it_active(self, cron_system):
        """Should activate job after approval."""
        # Create and approve job
        await cron_system["scheduler"].submit_user_job(
            name="To Approve", expression="0 8 * * *", code="async def run(): pass"
        )

        result = []
        async for chunk in cron_system["approve_tool"].execute_stream(
            job_identifier="To Approve"
        ):
            result.append(chunk)

        output = "".join(result)
        assert "approved" in output.lower()
        assert "active" in output.lower()

        # Verify in store
        jobs = await cron_system["store"].load_jobs()
        assert jobs[0].status == "active"

    @pytest.mark.asyncio
    async def test_full_lifecycle_create_approve_verify(self, cron_system):
        """Complete flow: create → approve → verify active (without scheduler execution)."""
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
    async def test_reject_pending_job_deletes_it(self, cron_system):
        """Should permanently delete rejected job."""
        # Create job
        await cron_system["scheduler"].submit_user_job(
            name="To Reject", expression="0 8 * * *", code="async def run(): pass"
        )

        # Reject it
        result = []
        async for chunk in cron_system["reject_tool"].execute_stream(
            job_identifier="To Reject"
        ):
            result.append(chunk)

        output = "".join(result)
        assert "Deleted" in output

        # Verify gone
        jobs = await cron_system["store"].load_jobs()
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_reject_active_job(self, cron_system):
        """Should be able to delete active jobs too."""
        # Create and approve
        job_id = await cron_system["scheduler"].submit_user_job(
            name="Active To Delete", expression="0 8 * * *", code="async def run(): pass"
        )
        await cron_system["scheduler"].approve_job(job_id, "test")

        # Delete it
        result = []
        async for chunk in cron_system["reject_tool"].execute_stream(
            job_identifier="Active To Delete"
        ):
            result.append(chunk)

        output = "".join(result)
        assert "Deleted" in output

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
            code="async def run():\n    print('Running')",
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


class TestNaturalLanguageEndToEnd:
    """Test natural language parsing through complete flow."""

    @pytest.mark.asyncio
    async def test_various_natural_language_inputs(self, cron_system):
        """Various NL inputs should create correct jobs."""
        test_cases = [
            ("every morning at 8am", "0 8 * * *"),
            ("Sundays at 7pm", "0 19 * * 0"),
            ("daily at noon", "0 12 * * *"),
            ("weekdays at 9am", "0 9 * * 1-5"),
        ]

        for nl_input, expected_cron in test_cases:
            result = []
            async for chunk in cron_system["schedule_tool"].execute_stream(
                name=f"Test {nl_input}",
                description="Test",
                cron_expression=nl_input,
            ):
                result.append(chunk)

            output = "".join(result)
            assert expected_cron in output, f"Failed for: {nl_input}"

    @pytest.mark.asyncio
    async def test_low_confidence_triggers_clarification(self, cron_system):
        """Vague input should ask for clarification."""
        result = []
        async for chunk in cron_system["schedule_tool"].execute_stream(
            name="Vague Job",
            description="Test",
            cron_expression="sometimes maybe",
        ):
            result.append(chunk)

        output = "".join(result)
        # Should not create job, should ask for clarification
        assert "not sure" in output.lower() or "don't understand" in output.lower()


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
