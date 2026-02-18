"""Core cron scheduler with async execution loop.

The CronScheduler manages job registration, monitors schedules,
and triggers execution on time.
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from src.cron import parser

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""

    ACTIVE = "active"
    PENDING = "pending"
    PAUSED = "paused"


@dataclass
class Job:
    """Cron job definition."""

    job_id: str
    name: str
    expression: str
    handler: Callable[[], Awaitable[None]]
    status: JobStatus = JobStatus.ACTIVE
    last_run: datetime | None = None
    _running: asyncio.Lock = field(default_factory=asyncio.Lock)


class CronScheduler:
    """Async job scheduler with cron-based execution.

    Manages job registration, monitors schedules, and triggers
    execution when jobs are due.
    """

    def __init__(self, check_interval: float = 60.0) -> None:
        """Initialize scheduler.

        Args:
            check_interval: Seconds between schedule checks
        """
        self._jobs: dict[str, Job] = {}
        self._task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._check_interval = check_interval

    async def start(self) -> None:
        """Start the scheduler monitoring loop."""
        if self._task is not None:
            return

        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Cron scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self._shutdown_event.set()

        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        logger.info("Cron scheduler stopped")

    def register_job(self, job: Job) -> None:
        """Register a job for execution.

        Args:
            job: Job to register
        """
        self._jobs[job.job_id] = job
        logger.debug(f"Registered job: {job.name} ({job.job_id})")

    async def _monitor_loop(self) -> None:
        """Background loop that checks job schedules."""
        while not self._shutdown_event.is_set():
            try:
                await self._check_jobs()
            except Exception:
                logger.exception("Error checking jobs")

            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self._check_interval,
                )

    async def _check_jobs(self) -> None:
        """Check all jobs and execute any that are due."""
        now = datetime.now(UTC)

        for job in self._jobs.values():
            if job.status != JobStatus.ACTIVE:
                continue

            try:
                should_run = parser.should_run(
                    job.expression,
                    job.last_run or datetime.min.replace(tzinfo=UTC),
                    now,
                )
            except ValueError:
                logger.warning(f"Invalid cron expression for job {job.job_id}: {job.expression}")
                continue

            if should_run:
                # Start execution without waiting (queue if already running)
                asyncio.create_task(self._execute_job(job))

    async def _execute_job(self, job: Job) -> None:
        """Execute a single job.

        Uses lock to ensure only one instance runs at a time.
        """
        if not job._running.locked():
            async with job._running:
                try:
                    logger.debug(f"Executing job: {job.name} ({job.job_id})")
                    await job.handler()
                    job.last_run = datetime.now(UTC)
                    logger.debug(f"Job completed: {job.name} ({job.job_id})")
                except Exception:
                    logger.exception(f"Job failed: {job.name} ({job.job_id})")
        else:
            logger.debug(f"Job already running, skipping: {job.name} ({job.job_id})")
