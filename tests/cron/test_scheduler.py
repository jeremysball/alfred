"""Tests for cron scheduler core functionality.

TDD approach: write tests first, then implement to make them pass.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cron.scheduler import CronScheduler, Job, JobStatus


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

    def test_register_job_adds_to_jobs(self):
        """register_job() adds job to internal dict."""
        scheduler = CronScheduler()
        job = Job(
            job_id="test-1",
            name="Test Job",
            expression="* * * * *",
            handler=AsyncMock(),
            status=JobStatus.ACTIVE,
        )
        
        scheduler.register_job(job)
        
        assert "test-1" in scheduler._jobs
        assert scheduler._jobs["test-1"] == job

    def test_register_job_overwrites_existing(self):
        """register_job() replaces job with same ID."""
        scheduler = CronScheduler()
        job1 = Job(
            job_id="test-1",
            name="Job 1",
            expression="* * * * *",
            handler=AsyncMock(),
            status=JobStatus.ACTIVE,
        )
        job2 = Job(
            job_id="test-1",
            name="Job 2",
            expression="*/5 * * * *",
            handler=AsyncMock(),
            status=JobStatus.ACTIVE,
        )
        
        scheduler.register_job(job1)
        scheduler.register_job(job2)
        
        assert scheduler._jobs["test-1"].name == "Job 2"


class TestCronSchedulerExecution:
    """Tests for job execution."""

    async def test_job_executes_on_schedule(self):
        """Job runs when should_run returns True."""
        scheduler = CronScheduler(check_interval=0.1)
        handler = AsyncMock()
        job = Job(
            job_id="test-exec",
            name="Test Execution",
            expression="* * * * *",  # Every minute
            handler=handler,
            status=JobStatus.ACTIVE,
            last_run=None,  # Never run
        )
        
        scheduler.register_job(job)
        await scheduler.start()
        
        # Wait for at least one check cycle
        await asyncio.sleep(0.15)
        
        await scheduler.stop()
        
        # Handler should have been called
        handler.assert_called_once()

    async def test_job_does_not_execute_if_not_due(self):
        """Job doesn't run if should_run returns False."""
        scheduler = CronScheduler(check_interval=0.1)
        handler = AsyncMock()
        job = Job(
            job_id="test-noexec",
            name="Test No Execution",
            expression="0 0 1 1 *",  # Once a year, Jan 1
            handler=handler,
            status=JobStatus.ACTIVE,
            last_run=datetime.now(timezone.utc),  # Just ran
        )
        
        scheduler.register_job(job)
        await scheduler.start()
        
        # Wait for check cycle
        await asyncio.sleep(0.15)
        
        await scheduler.stop()
        
        # Handler should not have been called
        handler.assert_not_called()

    async def test_job_queues_if_already_running(self):
        """Only one instance of job runs at a time."""
        scheduler = CronScheduler(check_interval=0.1)
        
        # Slow handler that takes 0.5 seconds
        async def slow_handler():
            await asyncio.sleep(0.5)
        
        handler = AsyncMock(side_effect=slow_handler)
        job = Job(
            job_id="test-queue",
            name="Test Queue",
            expression="* * * * *",
            handler=handler,
            status=JobStatus.ACTIVE,
            last_run=None,
        )
        
        scheduler.register_job(job)
        await scheduler.start()
        
        # Wait for first execution to start
        await asyncio.sleep(0.15)
        
        # Handler should be called once (in progress)
        assert handler.call_count == 1
        
        # Wait for second check cycle (while first still running)
        await asyncio.sleep(0.1)
        
        # Should still be 1 (queued, not started)
        assert handler.call_count == 1
        
        await scheduler.stop()

    async def test_pending_job_not_executed(self):
        """Jobs with PENDING status don't run."""
        scheduler = CronScheduler(check_interval=0.1)
        handler = AsyncMock()
        job = Job(
            job_id="test-pending",
            name="Test Pending",
            expression="* * * * *",
            handler=handler,
            status=JobStatus.PENDING,  # Pending approval
            last_run=None,
        )
        
        scheduler.register_job(job)
        await scheduler.start()
        
        await asyncio.sleep(0.15)
        
        await scheduler.stop()
        
        handler.assert_not_called()


class TestCronSchedulerMultipleJobs:
    """Tests for multiple job handling."""

    async def test_multiple_jobs_execute_independently(self):
        """Each job runs on its own schedule."""
        scheduler = CronScheduler(check_interval=0.1)
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        job1 = Job(
            job_id="job-1",
            name="Job 1",
            expression="* * * * *",
            handler=handler1,
            status=JobStatus.ACTIVE,
            last_run=None,
        )
        job2 = Job(
            job_id="job-2",
            name="Job 2",
            expression="* * * * *",
            handler=handler2,
            status=JobStatus.ACTIVE,
            last_run=None,
        )
        
        scheduler.register_job(job1)
        scheduler.register_job(job2)
        await scheduler.start()
        
        await asyncio.sleep(0.15)
        
        await scheduler.stop()
        
        handler1.assert_called_once()
        handler2.assert_called_once()


class TestCronSchedulerErrorHandling:
    """Tests for error handling."""

    async def test_job_error_does_not_crash_scheduler(self):
        """Handler exception doesn't stop scheduler."""
        scheduler = CronScheduler(check_interval=0.1)
        
        async def failing_handler():
            raise ValueError("Test error")
        
        handler = AsyncMock(side_effect=failing_handler)
        job = Job(
            job_id="test-error",
            name="Test Error",
            expression="* * * * *",
            handler=handler,
            status=JobStatus.ACTIVE,
            last_run=None,
        )
        
        scheduler.register_job(job)
        await scheduler.start()
        
        # Wait for check cycles
        await asyncio.sleep(0.25)
        
        # Scheduler should still be running
        assert scheduler._task is not None
        assert not scheduler._task.done()
        
        await scheduler.stop()


class TestCronSchedulerUpdateLastRun:
    """Tests for last_run tracking."""

    async def test_last_run_updated_after_execution(self):
        """Job's last_run is set after successful execution."""
        scheduler = CronScheduler(check_interval=0.1)
        handler = AsyncMock()
        job = Job(
            job_id="test-lastrun",
            name="Test Last Run",
            expression="* * * * *",
            handler=handler,
            status=JobStatus.ACTIVE,
            last_run=None,
        )
        
        scheduler.register_job(job)
        
        before = datetime.now(timezone.utc)
        await scheduler.start()
        await asyncio.sleep(0.15)
        await scheduler.stop()
        after = datetime.now(timezone.utc)
        
        assert job.last_run is not None
        assert before <= job.last_run <= after
