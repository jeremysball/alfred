"""Core cron scheduler with async execution loop.

The CronScheduler manages job registration, monitors schedules,
and triggers execution on time.
"""

import asyncio
import contextlib
import inspect
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, TypeGuard

from src.cron import parser
from src.cron.executor import ExecutionContext, JobExecutor
from src.cron.models import ExecutionRecord, ExecutionStatus, Job, JobStatus, ResourceLimits
from src.cron.observability import StructuredLogger
from src.cron.store import CronStore
from src.data_manager import get_data_dir
from src.type_defs import AsyncHandler

if TYPE_CHECKING:
    from src.config import Config
    from src.cron.socket_client import SocketClient

logger = logging.getLogger(__name__)


def is_async_handler(value: object) -> TypeGuard[AsyncHandler]:
    return callable(value) and inspect.iscoroutinefunction(value)


class JobApprovalResult(TypedDict):
    success: bool
    message: str


@dataclass
class RunnableJob:
    """Runtime job with compiled handler."""

    job_id: str
    name: str
    expression: str
    handler: AsyncHandler
    status: JobStatus = JobStatus.ACTIVE
    last_run: datetime | None = None
    _running: asyncio.Lock = field(default_factory=asyncio.Lock)

    @classmethod
    def from_job(cls, job: Job, handler: AsyncHandler) -> "RunnableJob":
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
        socket_client: "SocketClient | None" = None,
        config: "Config | None" = None,
    ) -> None:
        """Initialize scheduler.

        Args:
            store: CronStore for persistence (creates default if None)
            check_interval: Seconds between schedule checks
            data_dir: Directory for log files (default: XDG data dir)
            socket_client: Socket client for TUI communication (optional)
            config: Optional application config for system job settings
        """
        self._store = store or CronStore(data_dir)
        self._jobs: dict[str, RunnableJob] = {}
        self._job_code: dict[str, str] = {}  # Store code for each job
        self._task: asyncio.Task[None] | None = None
        self._shutdown_event = asyncio.Event()
        self._check_interval = check_interval
        self._socket_client = socket_client
        self._config = config

        # Initialize logger
        log_file = (data_dir or get_data_dir()) / "cron_logs.jsonl"
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

    async def reload_jobs(self) -> None:
        """Reload all jobs from the store.

        Called when SIGHUP is received to pick up external changes.
        """
        logger.info("Reloading jobs from store...")
        await self._load_jobs()
        logger.info(f"Reloaded {len(self._jobs)} jobs")

    async def register_job(self, job: Job) -> None:
        """Register a job for execution.

        Args:
            job: Job to register (will be persisted)

        Raises:
            ValueError: If job code fails to compile or doesn't define run() function
        """
        # Compile code to handler (raises ValueError on failure)
        handler = self._compile_handler(job.code)
        runnable = RunnableJob.from_job(job, handler)

        self._jobs[job.job_id] = runnable
        self._job_code[job.job_id] = job.code

        # Persist to store
        await self._store.save_job(job)
        logger.debug(f"Registered job: {job.name} ({job.job_id})")

    async def _register_system_job(
        self,
        job: Job,
        handler: AsyncHandler,
    ) -> None:
        """Register a system job with a provided handler."""
        runnable = RunnableJob.from_job(job, handler)
        self._jobs[job.job_id] = runnable
        self._job_code[job.job_id] = job.code

        await self._store.save_job(job)
        logger.debug(f"Registered system job: {job.name} ({job.job_id})")

    def _get_session_summarizer_expression(self, default_expression: str) -> str:
        """Build cron expression for session summarizer job."""
        if self._config is None:
            return default_expression

        interval = getattr(self._config, "session_cron_interval_minutes", None)
        if not isinstance(interval, int) or interval <= 0:
            logger.warning(
                "Invalid session_cron_interval_minutes=%s, using default",
                interval,
            )
            return default_expression

        return f"*/{interval} * * * *"

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
        )
        await self._store.save_job(job)
        logger.info(f"Submitted user job for approval: {name} ({job.job_id})")
        return job.job_id

    async def approve_job(self, job_id: str, approved_by: str) -> JobApprovalResult:
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
        """
        from src.cron.system_jobs import get_system_job, list_system_jobs

        for job_id in list_system_jobs():
            job_def = get_system_job(job_id)
            if job_def is None:
                logger.warning(f"System job {job_id} not found")
                continue

            # Check if already registered
            if job_id in self._jobs:
                logger.debug(f"System job {job_id} already registered")
                continue

            job = job_def.to_job()
            if job_id == "session_summarizer":
                job.expression = self._get_session_summarizer_expression(job.expression)

            await self._register_system_job(job, job_def.handler)
            logger.info(f"Registered system job: {job_id}")

    async def _load_jobs(self) -> None:
        """Load jobs from store and compile handlers."""
        jobs = await self._store.load_jobs()
        for job in jobs:
            if job.status == "active":
                try:
                    if job.handler_id:
                        from src.cron.system_jobs import get_system_job_handler

                        handler = get_system_job_handler(job.handler_id)
                        if handler is None:
                            logger.warning(
                                "System handler not found for job %s (%s)",
                                job.job_id,
                                job.handler_id,
                            )
                            continue
                        runnable = RunnableJob.from_job(job, handler)
                    else:
                        handler = self._compile_handler(job.code)
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
        namespace: dict[str, object] = {"__builtins__": {}}
        exec(compiled, namespace)  # noqa: S102

        if "run" not in namespace:
            raise ValueError("Job code must define a run() function")
        if not inspect.iscoroutinefunction(namespace["run"]):
            raise ValueError("Job run() function must be async (defined with 'async def')")

    def _compile_handler(self, code: str) -> AsyncHandler:
        """Compile job code into executable handler.

        Args:
            code: Python code as string

        Returns:
            Compiled async function

        Raises:
            ValueError: If code doesn't compile or lacks run() function
        """
        # Check for system job placeholder code
        if code.strip().startswith("# system job:"):
            raise ValueError(
                "System job code cannot be compiled directly - "
                "use handler_id to load system job handler"
            )

        async def _placeholder_notify(message: str) -> None:
            """Placeholder notify function - replaced at runtime."""
            pass

        # Full builtins access for jobs
        namespace: dict[str, object] = {
            "__builtins__": __builtins__,
            "notify": _placeholder_notify,
        }

        # Execute code in namespace
        exec(code, namespace)  # noqa: S102

        # Get the run function
        if "run" not in namespace:
            raise ValueError("Job code must define an async run() function")

        handler_value = namespace.get("run")
        if not is_async_handler(handler_value):
            raise ValueError("Job run() function must be async")

        return handler_value

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
        Records execution to store and logs.
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
            limits = job_model.resource_limits if job_model else ResourceLimits()

            # Create execution context
            context = ExecutionContext(
                job_id=job.job_id,
                job_name=job.name,
                socket_client=self._socket_client,
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
            logger.debug(f"Executing job: {job.name} ({job.job_id})")

            # Send job started notification
            if self._socket_client:
                from src.cron.socket_protocol import JobStartedMessage

                await self._socket_client.send(
                    JobStartedMessage(job_id=job.job_id, job_name=job.name)
                )

            # Execute with resource limits
            result = await executor.execute()

            end_time = datetime.now(UTC)

            # Log stdout/stderr for debugging
            if result.stdout:
                logger.debug("Job %s stdout:\n%s", job.job_id, result.stdout)
            if result.stderr:
                logger.debug("Job %s stderr:\n%s", job.job_id, result.stderr)

            # Update job state
            job.last_run = end_time
            if job.job_id in self._job_code:
                job_model = job.to_job(self._job_code[job.job_id])
                await self._store.save_job(job_model)

            # Log result
            if result.status == ExecutionStatus.SUCCESS:
                logger.debug("Job completed: %s (%s)", job.name, job.job_id)
                # Send completion notification
                if self._socket_client:
                    from src.cron.socket_protocol import JobCompletedMessage

                    stdout_preview = (result.stdout or "")[:200]
                    await self._socket_client.send(
                        JobCompletedMessage(
                            job_id=job.job_id,
                            job_name=job.name,
                            duration_ms=result.duration_ms,
                            stdout_preview=stdout_preview,
                        )
                    )
            elif result.status == ExecutionStatus.TIMEOUT:
                logger.warning("Job timed out: %s (%s)", job.name, job.job_id)
                # Send failure notification
                if self._socket_client:
                    from src.cron.socket_protocol import JobFailedMessage

                    await self._socket_client.send(
                        JobFailedMessage(
                            job_id=job.job_id,
                            job_name=job.name,
                            error="Job timed out",
                            duration_ms=result.duration_ms,
                        )
                    )
            else:
                logger.error("Job failed: %s (%s)", job.name, job.job_id)
                # Send failure notification
                if self._socket_client:
                    from src.cron.socket_protocol import JobFailedMessage

                    await self._socket_client.send(
                        JobFailedMessage(
                            job_id=job.job_id,
                            job_name=job.name,
                            error=result.error_message or "Unknown error",
                            duration_ms=result.duration_ms,
                        )
                    )

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
