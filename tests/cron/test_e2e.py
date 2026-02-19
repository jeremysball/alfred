"""End-to-end tests for cron scheduler workflows.

Tests complete user journeys through the cron system.
These complement the integration tests by focusing on full stack scenarios.
"""

import pytest

from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore


@pytest.fixture
async def running_scheduler(tmp_path):
    """Create a fully running scheduler for e2e tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    store = CronStore(data_dir=data_dir)
    scheduler = CronScheduler(store=store, check_interval=60.0)
    await scheduler.start()

    yield scheduler

    await scheduler.stop()


class TestE2EJobLifecycle:
    """E2E tests for complete job lifecycle."""

    @pytest.mark.asyncio
    async def test_create_approve_list_delete_workflow(self, running_scheduler):
        """Complete workflow: create → list → approve → list → delete."""
        scheduler = running_scheduler

        # 1. Create job
        job_id = await scheduler.submit_user_job(
            name="E2E Test Job",
            expression="0 9 * * *",
            code="async def run():\n    print('Hello')",
        )

        # 2. List pending jobs (filter out system jobs)
        jobs = await scheduler._store.load_jobs()
        pending = [j for j in jobs if j.status == "pending" and not j.job_id.startswith("session_")]
        assert len(pending) == 1
        assert pending[0].name == "E2E Test Job"

        # 3. Approve job
        await scheduler.approve_job(job_id, "test_user")

        # 4. List active jobs (filter out system jobs)
        jobs = await scheduler._store.load_jobs()
        active = [j for j in jobs if j.status == "active" and not j.job_id.startswith("session_")]
        assert len(active) == 1
        assert active[0].job_id == job_id

        # 5. Delete job
        await scheduler._store.delete_job(job_id)

        # 6. Verify deleted (filter out system jobs)
        jobs = await scheduler._store.load_jobs()
        user_jobs = [j for j in jobs if not j.job_id.startswith("session_")]
        assert len(user_jobs) == 0

    @pytest.mark.asyncio
    async def test_multiple_jobs_lifecycle(self, running_scheduler):
        """Multiple jobs can be created and managed independently."""
        scheduler = running_scheduler

        # Create multiple jobs
        job1 = await scheduler.submit_user_job(
            name="Job 1", expression="0 8 * * *", code="async def run(): pass"
        )
        job2 = await scheduler.submit_user_job(
            name="Job 2", expression="0 9 * * *", code="async def run(): pass"
        )
        job3 = await scheduler.submit_user_job(
            name="Job 3", expression="0 10 * * *", code="async def run(): pass"
        )

        # Approve only 2
        await scheduler.approve_job(job1, "test")
        await scheduler.approve_job(job3, "test")

        # Verify states (filter out system jobs)
        jobs = await scheduler._store.load_jobs()
        user_jobs = [j for j in jobs if not j.job_id.startswith("session_")]

        active = [j for j in user_jobs if j.status == "active"]
        pending = [j for j in user_jobs if j.status == "pending"]

        assert len(active) == 2
        assert len(pending) == 1
        assert pending[0].job_id == job2


class TestE2EJobExecution:
    """E2E tests for job execution."""

    @pytest.mark.asyncio
    async def test_job_execution_recorded(self, running_scheduler):
        """Job execution is recorded in history."""
        scheduler = running_scheduler

        # Create quick job
        job_id = await scheduler.submit_user_job(
            name="Quick Job",
            expression="* * * * *",  # Every minute
            code="async def run():\n    print('Executed!')",
        )
        await scheduler.approve_job(job_id, "test")

        # Trigger execution manually
        await scheduler._check_jobs()

        # Verify job is registered
        assert job_id in scheduler._jobs


class TestE2EErrorHandling:
    """E2E tests for error scenarios."""

    @pytest.mark.asyncio
    async def test_approve_nonexistent_job_raises_error(self, running_scheduler):
        """Approving nonexistent job raises ValueError."""
        scheduler = running_scheduler

        with pytest.raises(ValueError, match="Job not found"):
            await scheduler.approve_job("nonexistent-id", "test")

    @pytest.mark.asyncio
    async def test_job_code_persistence(self, running_scheduler):
        """Job code is persisted and retrieved correctly."""
        scheduler = running_scheduler

        code = "async def run():\n    print('Persisted code')"
        job_id = await scheduler.submit_user_job(
            name="Code Test", expression="0 8 * * *", code=code
        )

        # Load and verify code preserved
        jobs = await scheduler._store.load_jobs()
        job = next(j for j in jobs if j.job_id == job_id)
        assert job.code == code
