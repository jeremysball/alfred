"""Tests for cron scheduler core functionality.

TDD approach: write tests first, then implement to make them pass.
"""

import asyncio
from datetime import UTC, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.cron.models import Job
from src.cron.scheduler import CronScheduler, JobStatus, RunnableJob


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory."""
    return tmp_path / "data"


@pytest.fixture
def scheduler(temp_data_dir: Path) -> CronScheduler:
    """Create CronScheduler with temp directory."""
    return CronScheduler(check_interval=0.1)


class TestCronSchedulerInit:
    """Tests for CronScheduler initialization."""

    def test_scheduler_initializes_empty(self):
        """Scheduler starts with no jobs."""
        scheduler = CronScheduler()
        
        assert scheduler._jobs == {}
        assert scheduler._task is None
        assert not scheduler._shutdown_event.is_set()


class TestCronSchedulerStartStop:
    """Tests for start/stop lifecycle."""

    async def test_start_starts_monitor_loop(self):
        """start() launches background monitoring task."""
        scheduler = CronScheduler()
        
        await scheduler.start()
        
        assert scheduler._task is not None
        assert not scheduler._task.done()
        
        await scheduler.stop()

    async def test_stop_graceful_shutdown(self):
        """stop() cancels monitor loop cleanly."""
        scheduler = CronScheduler()
        await scheduler.start()
        
        await scheduler.stop()
        
        assert scheduler._shutdown_event.is_set()
        assert scheduler._task is None or scheduler._task.done()

    async def test_stop_without_start_succeeds(self):
        """stop() can be called even if start() was never called."""
        scheduler = CronScheduler()
        
        await scheduler.stop()  # Should not raise
        
        assert scheduler._shutdown_event.is_set()


class TestCronSchedulerRegisterJob:
    """Tests for job registration."""

    async def test_register_job_adds_to_jobs(self, scheduler: CronScheduler):
        """register_job() adds job to internal dict."""
        job = Job(
            job_id="test-1",
            name="Test Job",
            expression="* * * * *",
            code="async def run(): pass",
            status="active",
        )
        
        await scheduler.register_job(job)
        
        assert "test-1" in scheduler._jobs
        assert scheduler._jobs["test-1"].name == "Test Job"

    async def test_register_job_compiles_handler(self, scheduler: CronScheduler):
        """register_job() compiles code into executable handler."""
        job = Job(
            job_id="test-1",
            name="Test Job",
            expression="* * * * *",
            code="async def run(): return 'executed'",
            status="active",
        )
        
        await scheduler.register_job(job)
        
        # Handler should be compiled and callable
        assert asyncio.iscoroutinefunction(scheduler._jobs["test-1"].handler)

    async def test_register_job_overwrites_existing(self, scheduler: CronScheduler):
        """register_job() replaces job with same ID."""
        job1 = Job(
            job_id="test-1",
            name="Job 1",
            expression="* * * * *",
            code="async def run(): pass",
            status="active",
        )
        job2 = Job(
            job_id="test-1",
            name="Job 2",
            expression="*/5 * * * *",
            code="async def run(): pass",
            status="active",
        )
        
        await scheduler.register_job(job1)
        await scheduler.register_job(job2)
        
        assert scheduler._jobs["test-1"].name == "Job 2"


class TestCronSchedulerExecution:
    """Tests for job execution."""

    async def test_job_executes_on_schedule(self, scheduler: CronScheduler):
        """Job runs when should_run returns True."""
        job = Job(
            job_id="test-exec",
            name="Test Execution",
            expression="* * * * *",  # Every minute
            code="""
_executed = False
async def run():
    global _executed
    _executed = True
""",
            status="active",
            last_run=None,  # Never run
        )
        
        await scheduler.register_job(job)
        await scheduler.start()
        
        # Wait for at least one check cycle
        await asyncio.sleep(0.15)
        
        await scheduler.stop()
        
        # Job should have been marked as executed
        # (we check by seeing if last_run was updated)
        assert scheduler._jobs["test-exec"].last_run is not None

    async def test_job_does_not_execute_if_not_due(self, scheduler: CronScheduler):
        """Job doesn't run if should_run returns False."""
        job = Job(
            job_id="test-noexec",
            name="Test No Execution",
            expression="0 0 1 1 *",  # Once a year, Jan 1
            code="async def run(): pass",
            status="active",
            last_run=datetime.now(UTC),  # Just ran
        )
        
        await scheduler.register_job(job)
        original_last_run = scheduler._jobs["test-noexec"].last_run
        
        await scheduler.start()
        
        # Wait for check cycle
        await asyncio.sleep(0.15)
        
        await scheduler.stop()
        
        # last_run should not have changed
        assert scheduler._jobs["test-noexec"].last_run == original_last_run

    async def test_job_queues_if_already_running(self, scheduler: CronScheduler):
        """Only one instance of job runs at a time - verified via lock."""
        # Create a job and acquire its lock manually to simulate running state
        job = Job(
            job_id="test-queue",
            name="Test Queue",
            expression="* * * * *",
            code="async def run(): pass",
            status="active",
            last_run=None,
        )
        
        await scheduler.register_job(job)
        
        # Acquire the lock to simulate job currently running
        async with scheduler._jobs["test-queue"]._running:
            # Try to execute while locked - should skip
            await scheduler._execute_job(scheduler._jobs["test-queue"])
            
            # last_run should still be None (execution was skipped)
            assert scheduler._jobs["test-queue"].last_run is None
        
        # Now execute without lock - should succeed
        await scheduler._execute_job(scheduler._jobs["test-queue"])
        assert scheduler._jobs["test-queue"].last_run is not None

    async def test_pending_job_not_executed(self, scheduler: CronScheduler):
        """Jobs with pending status don't run."""
        # Note: pending jobs wouldn't normally be in _jobs dict
        # but we test the status check directly
        runnable = RunnableJob(
            job_id="test-pending",
            name="Test Pending",
            expression="* * * * *",
            handler=AsyncMock(),
            status=JobStatus.PENDING,
            last_run=None,
        )
        
        scheduler._jobs["test-pending"] = runnable
        await scheduler.start()
        
        await asyncio.sleep(0.15)
        
        await scheduler.stop()
        
        runnable.handler.assert_not_called()


class TestCronSchedulerMultipleJobs:
    """Tests for multiple job handling."""

    async def test_multiple_jobs_execute_independently(self, scheduler: CronScheduler):
        """Each job runs on its own schedule."""
        job1 = Job(
            job_id="job-1",
            name="Job 1",
            expression="* * * * *",
            code="async def run(): pass",
            status="active",
            last_run=None,
        )
        job2 = Job(
            job_id="job-2",
            name="Job 2",
            expression="* * * * *",
            code="async def run(): pass",
            status="active",
            last_run=None,
        )
        
        await scheduler.register_job(job1)
        await scheduler.register_job(job2)
        await scheduler.start()
        
        await asyncio.sleep(0.15)
        
        await scheduler.stop()
        
        # Both should have last_run set
        assert scheduler._jobs["job-1"].last_run is not None
        assert scheduler._jobs["job-2"].last_run is not None


class TestCronSchedulerErrorHandling:
    """Tests for error handling."""

    async def test_job_error_does_not_crash_scheduler(self, scheduler: CronScheduler):
        """Handler exception doesn't stop scheduler."""
        job = Job(
            job_id="test-error",
            name="Test Error",
            expression="* * * * *",
            code="async def run(): raise ValueError('Test error')",
            status="active",
            last_run=None,
        )
        
        await scheduler.register_job(job)
        await scheduler.start()
        
        # Wait for check cycles
        await asyncio.sleep(0.25)
        
        # Scheduler should still be running
        assert scheduler._task is not None
        assert not scheduler._task.done()
        
        await scheduler.stop()


class TestCronSchedulerUpdateLastRun:
    """Tests for last_run tracking."""

    async def test_last_run_updated_after_execution(self, scheduler: CronScheduler):
        """Job's last_run is set after successful execution."""
        job = Job(
            job_id="test-lastrun",
            name="Test Last Run",
            expression="* * * * *",
            code="async def run(): pass",
            status="active",
            last_run=None,
        )
        
        await scheduler.register_job(job)
        
        before = datetime.now(UTC)
        await scheduler.start()
        await asyncio.sleep(0.15)
        await scheduler.stop()
        after = datetime.now(UTC)
        
        assert scheduler._jobs["test-lastrun"].last_run is not None
        assert before <= scheduler._jobs["test-lastrun"].last_run <= after


class TestCronSchedulerCodeCompilation:
    """Tests for code compilation."""

    def test_compile_valid_code(self, scheduler: CronScheduler):
        """Valid async code compiles successfully."""
        code = """
async def run():
    return "hello"
"""
        handler = scheduler._compile_handler(code)
        
        assert asyncio.iscoroutinefunction(handler)

    def test_compile_missing_run_function(self, scheduler: CronScheduler):
        """Code without run() function raises error."""
        code = """
async def other_function():
    pass
"""
        with pytest.raises(ValueError, match="must define an async run\\(\\) function"):
            scheduler._compile_handler(code)

    def test_compile_non_async_run(self, scheduler: CronScheduler):
        """Non-async run() function raises error."""
        code = """
def run():
    pass
"""
        with pytest.raises(ValueError, match="must be async"):
            scheduler._compile_handler(code)
