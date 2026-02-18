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
from pathlib import Path
from typing import Any, cast

from src.cron import parser
from src.cron.executor import ExecutionContext, JobExecutor
from src.cron.models import ExecutionRecord, ExecutionStatus, Job
from src.cron.observability import Alert, HealthStatus, Observability
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
        data_dir: Path | None = None,
        observability: Observability | None = None,
    ) -> None:
        """Initialize scheduler.

        Args:
            store: CronStore for persistence (creates default if None)
            check_interval: Seconds between schedule checks
            data_dir: Directory for log files (default: data/)
            observability: Observability instance (creates default if None)
        """
        self._store = store or CronStore(data_dir)
        self._jobs: dict[str, RunnableJob] = {}
        self._job_code: dict[str, str] = {}  # Store code for each job
        self._task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._check_interval = check_interval

        # Initialize observability
        if observability:
            self._observability = observability
        else:
            log_file = (data_dir or Path("data")) / "cron_logs.jsonl"
            self._observability = Observability(log_file)

    async def start(self) -> None:
        """Start the scheduler monitoring loop.

        Loads jobs from store and registers system jobs before starting.
        """
        if self._task is not None:
            return

        # Load jobs from store
        await self._load_jobs()

        # Register system jobs
        await self.register_system_jobs()

        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._monitor_loop())
        self._observability.health.set_scheduler_running(True)
        await self._observability.logger.log_scheduler_event(
            "scheduler_start", "Cron scheduler started"
        )
        logger.info("Cron scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self._shutdown_event.set()
        self._observability.health.set_scheduler_running(False)

        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        await self._observability.logger.log_scheduler_event(
            "scheduler_stop", "Cron scheduler stopped"
        )
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

    async def register_system_jobs(self) -> None:
        """Register built-in system jobs.

        System jobs are pre-approved and run without human review.
        Currently includes session_ttl check every 5 minutes.
        """
        from src.cron.system_jobs import get_system_job_code

        system_jobs = ["session_ttl"]

        for job_id in system_jobs:
            job_info = get_system_job_code(job_id)
            if job_info is None:
                logger.warning(f"System job {job_id} not found")
                continue

            expression, code = job_info

            # Check if already registered
            if job_id in self._jobs:
                logger.debug(f"System job {job_id} already registered")
                continue

            job = Job(
                job_id=job_id,
                name=job_id.replace("_", " ").title(),
                expression=expression,
                code=code,
                status="active",
            )

            await self.register_job(job)
            logger.info(f"Registered system job: {job_id}")

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

        handler = cast(Callable[[], Awaitable[None]], namespace["run"])
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
        """Execute a single job with resource limits.

        Uses JobExecutor for timeout, memory monitoring, and output capture.
        Records execution to store and observability systems.
        """
        if job._running.locked():
            logger.debug(f"Job already running, skipping: {job.name} ({job.job_id})")
            return

        async with job._running:
            start_time = datetime.now(UTC)
            execution_id = str(uuid.uuid4())
            code_snapshot = self._job_code.get(job.job_id)

            # Get job model for resource limits
            job_model = job.to_job(code_snapshot) if code_snapshot else None
            limits = job_model.resource_limits if job_model else None

            # Create execution context
            context = ExecutionContext(
                job_id=job.job_id,
                job_name=job.name,
                notifier=None,  # TODO: Inject notifier when available
            )

            # Create executor and run
            job_for_executor = job_model or Job(
                job_id=job.job_id,
                name=job.name,
                expression=job.expression,
                code=code_snapshot or "",
            )
            executor = JobExecutor(
                job=job_for_executor,
                handler=job.handler,
                limits=limits,
                context=context,
            )

            # Record start in observability
            await self._observability.health.record_job_start(job.job_id)
            await self._observability.logger.log_job_start(
                job.job_id, job.name, code_snapshot
            )

            logger.debug(f"Executing job: {job.name} ({job.job_id})")

            # Execute with resource limits
            result = await executor.execute()

            end_time = datetime.now(UTC)

            # Update job state
            job.last_run = end_time
            if job.job_id in self._job_code:
                job_model = job.to_job(self._job_code[job.job_id])
                await self._store.save_job(job_model)

            # Log result
            if result.status == ExecutionStatus.SUCCESS:
                logger.debug(f"Job completed: {job.name} ({job.job_id})")
            elif result.status == ExecutionStatus.TIMEOUT:
                logger.warning(f"Job timed out: {job.name} ({job.job_id})")
            else:
                logger.error(f"Job failed: {job.name} ({job.job_id})")

            # Record execution
            record = ExecutionRecord(
                execution_id=execution_id,
                job_id=job.job_id,
                started_at=start_time,
                ended_at=end_time,
                status=result.status,
                duration_ms=result.duration_ms,
                error_message=result.error_message,
                stdout=result.stdout or None,
                stderr=result.stderr or None,
                memory_peak_mb=result.memory_peak_mb,
                stdout_truncated=result.stdout_truncated,
            )
            await self._store.record_execution(record)

            # Record end in observability
            await self._observability.health.record_job_end(job.job_id)
            await self._observability.logger.log_job_end(
                job.job_id, job.name, record, code_snapshot
            )

            # Update metrics
            await self._observability.metrics.jobs_executed.increment()
            await self._observability.metrics.job_duration_ms.observe(result.duration_ms)
            if result.status == ExecutionStatus.FAILED:
                await self._observability.metrics.job_failures.increment()

            # Check for alerts
            alerts = await self._observability.alerts.record_execution(
                job.job_id, result.status == ExecutionStatus.SUCCESS, result.duration_ms
            )
            for alert in alerts:
                logger.warning(f"Alert: {alert.message}")

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics from the observability system.

        Returns:
            Dictionary containing all metrics
        """
        return self._observability.metrics.to_dict()

    async def health_check(self) -> HealthStatus:
        """Perform a health check on the scheduler.

        Returns:
            HealthStatus with current health information
        """
        # Update stuck jobs from health checker
        health = await self._observability.health.check_health()

        # Generate any alerts from health issues
        alerts = await self._observability.alerts.check_stuck_jobs(
            health.stuck_jobs, health
        )
        for alert in alerts:
            logger.warning(f"Health alert: {alert.message}")

        return health

    async def check_and_alert(self) -> list[Alert]:
        """Check health and generate alerts.

        Returns:
            List of alerts generated
        """
        health = await self.health_check()
        return await self._observability.alerts.check_stuck_jobs(
            health.stuck_jobs, health
        )
