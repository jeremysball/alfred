"""Core cron scheduler with async execution loop.

The CronScheduler manages job registration, monitors schedules,
and triggers execution on time.
"""

import asyncio
import contextlib
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.cron import parser
from src.cron.models import ExecutionRecord, ExecutionStatus, Job
from src.cron.store import CronStore

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""

    ACTIVE = "active"
    PENDING = "pending"
    PAUSED = "paused"


@dataclass
class RunnableJob:
    """Runtime job with compiled handler."""

    job_id: str
    name: str
    expression: str
    handler: Callable[[], Awaitable[None]]
    status: JobStatus = JobStatus.ACTIVE
    last_run: datetime | None = None
    _running: asyncio.Lock = field(default_factory=asyncio.Lock)

    @classmethod
    def from_job(cls, job: Job, handler: Callable[[], Awaitable[None]]) -> "RunnableJob":
        """Create RunnableJob from Job model and handler."""
        return cls(
            job_id=job.job_id,
            name=job.name,
            expression=job.expression,
            handler=handler,
            status=JobStatus(job.status) if isinstance(job.status, str) else job.status,
            last_run=job.last_run,
        )

    def to_job(self, code: str) -> Job:
        """Convert back to Job model for persistence."""
        return Job(
            job_id=self.job_id,
            name=self.name,
            expression=self.expression,
            code=code,
            status=self.status.value if isinstance(self.status, Enum) else self.status,
            last_run=self.last_run,
        )


class CronScheduler:
    """Async job scheduler with cron-based execution.

    Manages job registration, monitors schedules, and triggers
    execution when jobs are due. Integrates with CronStore for
    persistence.
    """

    def __init__(
        self,
        store: CronStore | None = None,
        check_interval: float = 60.0,
    ) -> None:
        """Initialize scheduler.

        Args:
            store: CronStore for persistence (creates default if None)
            check_interval: Seconds between schedule checks
        """
        self._store = store or CronStore()
        self._jobs: dict[str, RunnableJob] = {}
        self._job_code: dict[str, str] = {}  # Store code for each job
        self._task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._check_interval = check_interval

    async def start(self) -> None:
        """Start the scheduler monitoring loop.

        Loads jobs from store before starting.
        """
        if self._task is not None:
            return

        # Load jobs from store
        await self._load_jobs()

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

    async def register_job(self, job: Job) -> None:
        """Register a job for execution.

        Args:
            job: Job to register (will be persisted)
        """
        # Compile code to handler
        handler = self._compile_handler(job.code)
        runnable = RunnableJob.from_job(job, handler)

        self._jobs[job.job_id] = runnable
        self._job_code[job.job_id] = job.code

        # Persist to store
        await self._store.save_job(job)
        logger.debug(f"Registered job: {job.name} ({job.job_id})")

    async def submit_user_job(
        self,
        name: str,
        expression: str,
        code: str,
    ) -> str:
        """Submit a user job for approval.

        Args:
            name: Job name
            expression: Cron expression
            code: Python code as string

        Returns:
            Job ID (pending approval)
        """
        job = Job(
            job_id=str(uuid.uuid4()),
            name=name,
            expression=expression,
            code=code,
            status="pending",
        )
        await self._store.save_job(job)
        logger.info(f"Submitted user job for approval: {name} ({job.job_id})")
        return job.job_id

    async def approve_job(self, job_id: str, approved_by: str) -> None:
        """Approve a pending user job.

        Args:
            job_id: Job ID to approve
            approved_by: Who approved the job
        """
        jobs = await self._store.load_jobs()
        for job in jobs:
            if job.job_id == job_id:
                job.status = "active"
                await self._store.save_job(job)
                # Register for execution
                await self.register_job(job)
                logger.info(f"Approved job {job_id} by {approved_by}")
                return
        raise ValueError(f"Job not found: {job_id}")

    async def _load_jobs(self) -> None:
        """Load jobs from store and compile handlers."""
        jobs = await self._store.load_jobs()
        for job in jobs:
            if job.status == "active":
                try:
                    handler = self._compile_handler(job.code)
                    runnable = RunnableJob.from_job(job, handler)
                    self._jobs[job.job_id] = runnable
                    self._job_code[job.job_id] = job.code
                    logger.debug(f"Loaded job: {job.name} ({job.job_id})")
                except Exception:
                    logger.exception(f"Failed to load job {job.job_id}")

    def _compile_handler(self, code: str) -> Callable[[], Awaitable[None]]:
        """Compile job code into executable handler.

        Args:
            code: Python code as string

        Returns:
            Compiled async function
        """
        # Create namespace with allowed builtins
        namespace: dict[str, Any] = {
            "__builtins__": {
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
            },
        }

        # Execute code in namespace
        exec(code, namespace)  # noqa: S102

        # Get the run function
        if "run" not in namespace:
            raise ValueError("Job code must define an async run() function")

        handler = namespace["run"]
        if not asyncio.iscoroutinefunction(handler):
            raise ValueError("Job run() function must be async")

        return handler

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

    async def _execute_job(self, job: RunnableJob) -> None:
        """Execute a single job.

        Uses lock to ensure only one instance runs at a time.
        Records execution to store.
        """
        if job._running.locked():
            logger.debug(f"Job already running, skipping: {job.name} ({job.job_id})")
            return

        async with job._running:
            start_time = datetime.now(UTC)
            execution_id = str(uuid.uuid4())
            error_message = None

            try:
                logger.debug(f"Executing job: {job.name} ({job.job_id})")
                await job.handler()
                job.last_run = datetime.now(UTC)

                # Persist updated last_run
                if job.job_id in self._job_code:
                    job_model = job.to_job(self._job_code[job.job_id])
                    await self._store.save_job(job_model)

                logger.debug(f"Job completed: {job.name} ({job.job_id})")
                status = ExecutionStatus.SUCCESS

            except Exception as e:
                logger.exception(f"Job failed: {job.name} ({job.job_id})")
                error_message = str(e)
                status = ExecutionStatus.FAILED

            finally:
                end_time = datetime.now(UTC)
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                # Record execution
                record = ExecutionRecord(
                    execution_id=execution_id,
                    job_id=job.job_id,
                    started_at=start_time,
                    ended_at=end_time,
                    status=status,
                    duration_ms=duration_ms,
                    error_message=error_message,
                )
                await self._store.record_execution(record)
