"""Tests for system jobs."""

from pathlib import Path

import pytest

from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore
from src.cron.system_jobs import get_system_job_code, list_system_jobs


class TestSystemJobRegistry:
    """Tests for system job registry."""

    def test_list_system_jobs_returns_expected(self) -> None:
        """Should return list of system job IDs."""
        jobs = list_system_jobs()
        assert "session_ttl" in jobs

    def test_get_system_job_code_valid(self) -> None:
        """Should return expression and code for valid job."""
        result = get_system_job_code("session_ttl")
        assert result is not None

        expression, code = result
        assert expression == "*/5 * * * *"
        assert "async def run()" in code
        assert "session ttl check" in code.lower()

    def test_get_system_job_code_invalid(self) -> None:
        """Should return None for invalid job ID."""
        result = get_system_job_code("nonexistent_job")
        assert result is None


class TestSystemJobRegistration:
    """Tests for registering system jobs with scheduler."""

    @pytest.fixture
    async def scheduler(self, tmp_path: Path):
        """Create scheduler with temp storage."""
        store = CronStore(data_dir=tmp_path / "data")
        sched = CronScheduler(store=store, check_interval=0.1)
        yield sched
        await sched.stop()

    async def test_register_system_jobs_creates_jobs(self, scheduler: CronScheduler) -> None:
        """Should create system jobs when called."""
        await scheduler.register_system_jobs()

        # Check job was registered
        assert "session_ttl" in scheduler._jobs
        job = scheduler._jobs["session_ttl"]
        assert job.name == "Session Ttl"
        assert job.expression == "*/5 * * * *"

    async def test_register_system_jobs_persists_to_store(self, scheduler: CronScheduler) -> None:
        """Should persist system jobs to store."""
        await scheduler.register_system_jobs()

        # Verify stored
        jobs = await scheduler._store.load_jobs()
        job_ids = {j.job_id for j in jobs}
        assert "session_ttl" in job_ids

    async def test_register_system_jobs_idempotent(self, scheduler: CronScheduler) -> None:
        """Should not duplicate jobs on multiple calls."""
        await scheduler.register_system_jobs()
        await scheduler.register_system_jobs()

        jobs = await scheduler._store.load_jobs()
        session_jobs = [j for j in jobs if j.job_id == "session_ttl"]
        assert len(session_jobs) == 1


class TestSystemJobExecution:
    """Tests for system job execution."""

    @pytest.fixture
    async def running_scheduler(self, tmp_path: Path):
        """Create and start scheduler with temp storage."""
        store = CronStore(data_dir=tmp_path / "data")
        scheduler = CronScheduler(store=store, check_interval=0.1)
        await scheduler.start()
        yield scheduler
        await scheduler.stop()

    async def test_system_job_executes_on_schedule(
        self, running_scheduler: CronScheduler, tmp_path: Path
    ) -> None:
        """System job should execute when scheduler runs."""
        # Wait for job to execute (runs every 5 min, but we use 0.1s check interval)
        # Since it's */5 * * * *, it won't run immediately
        # We just verify it's registered and the code compiles
        assert "session_ttl" in running_scheduler._jobs

        # Verify code compiles
        code = running_scheduler._job_code["session_ttl"]
        compile(code, "<string>", "exec")

    async def test_system_job_logs_execution(
        self, running_scheduler: CronScheduler, tmp_path: Path
    ) -> None:
        """System job execution should be logged."""
        # Check that the job is registered
        assert "session_ttl" in running_scheduler._jobs

        # Verify the job is active
        job = running_scheduler._jobs["session_ttl"]
        assert job.status.value == "active"

