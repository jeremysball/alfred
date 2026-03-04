"""Core cron scheduler with async execution loop.

The CronScheduler manages job registration, monitors schedules,
and triggers execution on time.
"""

import asyncio
import contextlib
import inspect
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
from src.cron.models import ExecutionRecord, ExecutionStatus, Job, JobStatus, ResourceLimits
from src.cron.notifier import Notifier
from src.cron.observability import StructuredLogger
from src.cron.sandbox import SANDBOX_BUILTINS
from src.cron.store import CronStore

logger = logging.getLogger(__name__)


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
        notifier: Notifier | None = None,
    ) -> None:
        """Initialize scheduler.

        Args:
            store: CronStore for persistence (creates default if None)
            check_interval: Seconds between schedule checks
            data_dir: Directory for log files (default: data/)
            notifier: Notifier for sending messages to users (optional)
        """
        self._store = store or CronStore(data_dir)
        self._jobs: dict[str, RunnableJob] = {}
        self._job_code: dict[str, str] = {}  # Store code for each job
        self._task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._check_interval = check_interval
        self._notifier = notifier

        # Initialize logger
        log_file = (data_dir or Path("data")) / "cron_logs.jsonl"
        self._logger = StructuredLogger(log_file)

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
        await self._logger.log_scheduler_event("scheduler_start", "Cron scheduler started")
        logger.info("Cron scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self._shutdown_event.set()

        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        await self._logger.log_scheduler_event("scheduler_stop", "Cron scheduler stopped")
        logger.info("Cron scheduler stopped")

    async def register_job(self, job: Job) -> None:
        """Register a job for execution.

        Args:
            job: Job to register (will be persisted)

        Raises:
            ValueError: If job code fails to compile or doesn't define run() function
        """
        # Compile code to handler (raises ValueError on failure)
        handler = self._compile_handler(job.code, job.sandbox_enabled)
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
        sandbox_enabled: bool = False,
    ) -> str:
        """Submit a user job for approval.

        Args:
            name: Job name
            expression: Cron expression
            code: Python code as string
            sandbox_enabled: Whether to run in sandbox with restricted builtins

        Returns:
            Job ID (pending approval)

        Raises:
            ValueError: If code fails validation (compile error or missing run function)
        """
        # Validate code compiles and has run() function before saving
        self._validate_job_code(code)

        job = Job(
            job_id=str(uuid.uuid4()),
            name=name,
            expression=expression,
            code=code,
            status="pending",
            sandbox_enabled=sandbox_enabled,
        )
        await self._store.save_job(job)
        logger.info(f"Submitted user job for approval: {name} ({job.job_id})")
        return job.job_id

    async def approve_job(self, job_id: str, approved_by: str) -> dict[str, Any]:
        """Approve a pending user job.

        Args:
            job_id: Job ID to approve
            approved_by: Who approved the job

        Returns:
            Dictionary with 'success' bool and 'message' string
        """
        jobs = await self._store.load_jobs()
        for job in jobs:
            if job.job_id == job_id:
                try:
                    # Try to compile before updating status
                    self._validate_job_code(job.code)
                    job.status = "active"
                    await self._store.save_job(job)
                    # Register for execution
                    await self.register_job(job)
                    logger.info(f"Approved job {job_id} by {approved_by}")
                    return {"success": True, "message": f"Job '{job.name}' approved and activated"}
                except ValueError as e:
                    logger.error(f"Failed to approve job {job_id}: {e}")
                    return {"success": False, "message": f"Cannot approve job: {e}"}
                except Exception as e:
                    logger.exception(f"Unexpected error approving job {job_id}")
                    return {"success": False, "message": f"Unexpected error: {e}"}
        return {"success": False, "message": f"Job not found: {job_id}"}

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
                    handler = self._compile_handler(job.code, job.sandbox_enabled)
                    runnable = RunnableJob.from_job(job, handler)
                    self._jobs[job.job_id] = runnable
                    self._job_code[job.job_id] = job.code
                    logger.debug(f"Loaded job: {job.name} ({job.job_id})")
                except Exception:
                    logger.exception(f"Failed to load job {job.job_id}")

    def _validate_job_code(self, code: str) -> None:
        """Validate job code compiles and has required run() function.

        Args:
            code: Python code as string

        Raises:
            ValueError: If code doesn't compile or lacks run() function
        """
        try:
            compiled = compile(code, "<string>", "exec")
        except SyntaxError as e:
            raise ValueError(f"Syntax error in job code: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to compile job code: {e}") from e

        # Check for run function by examining bytecode
        namespace: dict[str, Any] = {"__builtins__": {}}
        exec(compiled, namespace)  # noqa: S102

        if "run" not in namespace:
            raise ValueError("Job code must define a run() function")
        if not inspect.iscoroutinefunction(namespace["run"]):
            raise ValueError("Job run() function must be async (defined with 'async def')")

    def _compile_handler(
        self, code: str, sandbox_enabled: bool = False
    ) -> Callable[[], Awaitable[None]]:
        """Compile job code into executable handler.

        Args:
            code: Python code as string
            sandbox_enabled: If True, use restricted builtins. If False, full access.

        Returns:
            Compiled async function

        Raises:
            ValueError: If code doesn't compile or lacks run() function
        """

        async def _placeholder_notify(message: str) -> None:
            """Placeholder notify function - replaced at runtime."""
            pass

        if sandbox_enabled:
            # Restricted builtins for sandboxed jobs
            namespace: dict[str, Any] = {
                "__builtins__": SANDBOX_BUILTINS,
                "notify": _placeholder_notify,
            }
        else:
            # Full builtins access for non-sandboxed jobs
            namespace = {
                "__builtins__": __builtins__,
                "notify": _placeholder_notify,
            }

        # Execute code in namespace
        exec(code, namespace)  # noqa: S102

        # Get the run function
        if "run" not in namespace:
            raise ValueError("Job code must define an async run() function")

        handler = cast(Callable[[], Awaitable[None]], namespace["run"])
        if not inspect.iscoroutinefunction(handler):
            raise ValueError("Job run() function must be async")

        return handler

    async def _monitor_loop(self) -> None:
        """Background loop that checks job schedules."""
        logger.debug(f"Monitor loop started, check interval: {self._check_interval}s")
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
        logger.debug(f"Checking {len(self._jobs)} jobs at {now.isoformat()}")

        jobs_due = []
        for job in self._jobs.values():
            if job.status != JobStatus.ACTIVE:
                logger.debug(f"Skipping inactive job: {job.name} (status={job.status})")
                continue

            try:
                should_run = parser.should_run(
                    job.expression,
                    job.last_run or datetime.min.replace(tzinfo=UTC),
                    now,
                )
                if should_run:
                    jobs_due.append(job)
                    logger.debug(f"Job due: {job.name} ({job.job_id}), expression={job.expression}")
            except ValueError as e:
                logger.warning(
                    f"Invalid cron expression for job {job.job_id}: "
                    f"{job.expression} - {e}"
                )
                continue

        if jobs_due:
            logger.info(f"Found {len(jobs_due)} job(s) due for execution")

        for job in jobs_due:
            # Start execution without waiting (queue if already running)
            logger.debug(f"Creating task for job: {job.name}")
            asyncio.create_task(self._execute_job(job))

    async def _execute_job(self, job: RunnableJob) -> None:
        """Execute a single job with resource limits.

        Uses JobExecutor for timeout, memory monitoring, and output capture.
        Records execution to store and logs.
        """
        if job._running.locked():
            logger.info(f"Job already running, skipping: {job.name} ({job.job_id})")
            return

        logger.info(f"Starting execution of job: {job.name} ({job.job_id})")

        async with job._running:
            start_time = datetime.now(UTC)
            execution_id = str(uuid.uuid4())
            code_snapshot = self._job_code.get(job.job_id)

            # Get job model for resource limits
            job_model = job.to_job(code_snapshot) if code_snapshot else None
            limits = job_model.resource_limits if job_model else ResourceLimits()
            logger.debug(
                f"Job {job.name} resource limits: timeout={limits.timeout_seconds}s, "
                f"max_memory={limits.max_memory_mb}MB"
            )

            # Create execution context
            context = ExecutionContext(
                job_id=job.job_id,
                job_name=job.name,
                notifier=self._notifier,
                chat_id=job_model.chat_id if job_model else None,
            )
            logger.debug(
                f"Job {job.name} notifier: "
                f"{type(self._notifier).__name__ if self._notifier else 'None'}"
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

            # Log start
            await self._logger.log_job_start(job.job_id, job.name, code_snapshot)
            logger.debug(f"Executing job handler: {job.name} ({job.job_id})")

            # Execute with resource limits
            try:
                result = await executor.execute()
            except Exception:
                logger.exception(f"Job executor crashed: {job.name} ({job.job_id})")
                raise

            end_time = datetime.now(UTC)

            # Update job state
            job.last_run = end_time
            if job.job_id in self._job_code:
                job_model = job.to_job(self._job_code[job.job_id])
                await self._store.save_job(job_model)

            # Log result with details
            if result.status == ExecutionStatus.SUCCESS:
                logger.info(
                    f"Job completed successfully: {job.name} ({job.job_id}) "
                    f"in {result.duration_ms}ms, memory_peak={result.memory_peak_mb}MB"
                )
            elif result.status == ExecutionStatus.TIMEOUT:
                logger.warning(
                    f"Job timed out: {job.name} ({job.job_id}) "
                    f"after {result.duration_ms}ms (limit={limits.timeout_seconds}s)"
                )
            else:
                logger.error(
                    f"Job failed: {job.name} ({job.job_id}) "
                    f"after {result.duration_ms}ms - {result.error_message}"
                )
                if result.stderr:
                    logger.error(f"Job stderr: {result.stderr[:500]}")

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

            # Log end
            await self._logger.log_job_end(job.job_id, job.name, record, code_snapshot)
