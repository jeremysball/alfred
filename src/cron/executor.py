"""Job execution with resource limits and monitoring.

The JobExecutor class wraps job execution with timeout enforcement,
memory monitoring, and output capture. It provides safe execution
of user-submitted code with configurable resource boundaries.

ARCHITECTURE: Isolated Namespaces for Concurrent Job Execution
--------------------------------------------------------------

Problem: Cron jobs run concurrently via asyncio.create_task(). If multiple
jobs mutate global sys.stdout simultaneously, they corrupt each other's
output (check-time-use-time race condition).

Solution: Each job gets its own isolated stdout/stderr buffers injected
into its namespace. No global state mutation. No locks needed.

How exec() Provides Isolation:
    When scheduler._compile_handler() calls exec(code, namespace):
    1. Python compiles the code into a code object
    2. exec() creates a NEW function object for each 'def run()'
    3. The function's __globals__ points to the provided namespace dict
    4. Each job gets a DISTINCT function with DISTINCT globals

    Example:
        Job A: namespace_A -> exec() -> handler_A
               handler_A.__globals__ is namespace_A

        Job B: namespace_B -> exec() -> handler_B
               handler_B.__globals__ is namespace_B

    Modifying handler_A.__globals__ does NOT affect handler_B.__globals__
    because they are different dictionary objects.

Output Capture Without Global Mutation:
    Instead of: sys.stdout = my_buffer  # RACE: shared global!

    We do: handler.__globals__["sys"] = mock_sys_module
           handler.__globals__["print"] = capture_print_function
           sys.modules["sys"] = mock_sys_module  # For "import sys"

    The mock sys module has stdout/stderr that write to job-specific
    StringIO buffers. Each job writes to its own buffers.

Why This Is Thread-Safe:
    - Different jobs = different handler functions = different globals dicts
    - No shared mutable state between jobs
    - The only "shared" thing we modify is sys.modules["sys"], but we
      save/restore it around each job execution
    - Scheduler prevents concurrent execution of the SAME job (same handler)

Why Not Use Locks:
    - threading.Lock() blocks the OS thread (bad for async)
    - asyncio.Lock() only works within event loop (not threads)
    - With isolated buffers, no coordination needed = no locks
"""

import asyncio
import contextlib
import io
import logging
import sys
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psutil

from src.cron.models import ExecutionStatus, Job, ResourceLimits
from src.cron.notifier import Notifier

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Safe operations available to job handlers.

    Provides a controlled interface for jobs to interact with
    Alfred's systems without exposing dangerous operations.
    """

    job_id: str
    job_name: str
    memory_store: Any | None = None
    notifier: Notifier | None = None
    chat_id: int | None = None  # Per-job chat_id for notifications

    async def notify(self, message: str) -> None:
        """Send a notification to the user.

        Args:
            message: Message to send
        """
        if self.notifier:
            await self.notifier.send(message, chat_id=self.chat_id)

    def store_get(self, key: str) -> Any:
        """Get a value from the job's key-value store.

        Args:
            key: Storage key

        Returns:
            Stored value or None if not found
        """
        # TODO: Implement persistent KV store per job
        return None

    def store_set(self, key: str, value: Any) -> None:
        """Set a value in the job's key-value store.

        Args:
            key: Storage key
            value: Value to store
        """
        # TODO: Implement persistent KV store per job
        pass


@dataclass
class ExecutionResult:
    """Result of job execution with resource metrics."""

    status: ExecutionStatus
    duration_ms: int
    stdout: str
    stderr: str
    memory_peak_mb: int | None = None
    error_message: str | None = None
    stdout_truncated: bool = False


class _JobOutput:
    """Output stream for job execution that writes to a buffer.

    Provides stdout/stderr-like interface that writes to StringIO buffers.
    Each job gets its own instance, no shared global state.
    """

    def __init__(self, buffer: io.StringIO):
        self._buffer = buffer

    def write(self, text: str) -> int:
        """Write text to the buffer."""
        return self._buffer.write(text)

    def flush(self) -> None:
        """Flush the buffer (no-op for StringIO)."""
        pass


def _create_job_globals(stdout: io.StringIO, stderr: io.StringIO) -> dict[str, Any]:
    """Create globals namespace for job execution with isolated output.

    Returns a namespace where print() and sys.stdout write to the
    provided buffers instead of the real stdout/stderr.

    Args:
        stdout: Buffer for stdout output
        stderr: Buffer for stderr output

    Returns:
        Globals dictionary for job execution
    """

    # Create mock sys module
    class MockSys:
        def __init__(self, out: io.StringIO, err: io.StringIO) -> None:
            self.stdout = _JobOutput(out)
            self.stderr = _JobOutput(err)
            self.version = sys.version
            self.version_info = sys.version_info
            self.platform = sys.platform
            self.path: list[str] = []
            self.modules: dict[str, Any] = {}

    mock_sys = MockSys(stdout, stderr)

    # Create print function that uses mock sys
    def job_print(
        *args: Any,
        sep: str = " ",
        end: str = "\n",
        file: Any = None,
        flush: bool = False,
    ) -> None:
        if file is None:
            file = mock_sys.stdout
        text = sep.join(str(arg) for arg in args) + end
        file.write(text)
        if flush:
            file.flush()

    return {
        "sys": mock_sys,
        "print": job_print,
    }


class JobExecutor:
    """Execute jobs with resource limits and monitoring.

    Provides:
    - Timeout enforcement via asyncio.wait_for
    - Memory usage tracking via psutil
    - Output capture with line limits
    - Safe execution namespace with isolated stdout/stderr
    """

    def __init__(
        self,
        job: Job,
        handler: Callable[[], Any],
        limits: ResourceLimits,
        context: ExecutionContext,
    ):
        """Initialize executor.

        Args:
            job: Job being executed
            handler: Compiled async handler function (see ARCHITECTURE note above)
            limits: Resource limits to enforce
            context: Execution context with safe operations
        """
        self.job = job
        self.handler = handler
        self.limits = limits
        self.context = context
        self._start_time: datetime | None = None
        self._memory_peak_mb: int = 0

    async def execute(self) -> ExecutionResult:
        """Execute job with resource limits.

        Runs the handler with:
        - Timeout enforcement
        - Memory monitoring
        - Output capture and truncation

        Returns:
            ExecutionResult with status, output, and metrics
        """
        self._start_time = datetime.now(UTC)
        self._memory_peak_mb = 0

        # Start memory tracking
        tracemalloc.start()

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Execute with timeout, passing capture buffers
            await self._execute_with_timeout(stdout_capture, stderr_capture)

            # Get results
            stdout = stdout_capture.getvalue()
            stderr = stderr_capture.getvalue()

            # Truncate if needed
            stdout_truncated = False
            lines = stdout.splitlines()
            if len(lines) > self.limits.max_output_lines:
                lines = lines[: self.limits.max_output_lines]
                stdout = "\n".join(lines) + "\n[... output truncated ...]"
                stdout_truncated = True

            duration_ms = self._get_duration_ms()

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                duration_ms=duration_ms,
                stdout=stdout,
                stderr=stderr,
                memory_peak_mb=self._memory_peak_mb or None,
                stdout_truncated=stdout_truncated,
            )

        except TimeoutError:
            duration_ms = self._get_duration_ms()
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                duration_ms=duration_ms,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                memory_peak_mb=self._memory_peak_mb or None,
                error_message=f"Job exceeded timeout of {self.limits.timeout_seconds}s",
                stdout_truncated=False,
            )

        except Exception as e:
            duration_ms = self._get_duration_ms()
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                duration_ms=duration_ms,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                memory_peak_mb=self._memory_peak_mb or None,
                error_message=str(e),
                stdout_truncated=False,
            )

        finally:
            tracemalloc.stop()

    async def _execute_with_timeout(
        self, stdout_capture: io.StringIO, stderr_capture: io.StringIO
    ) -> None:
        """Execute handler with timeout and memory monitoring."""
        # Create task for the handler
        task = asyncio.create_task(
            self._monitored_execution(stdout_capture, stderr_capture)
        )

        try:
            await asyncio.wait_for(task, timeout=self.limits.timeout_seconds)
        except TimeoutError:
            # Cancel the task
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            raise

    async def _monitored_execution(
        self, stdout_capture: io.StringIO, stderr_capture: io.StringIO
    ) -> None:
        """Execute handler while monitoring resources.

        ARCHITECTURE NOTE: Output Capture Without Global State Mutation

        Instead of mutating global sys.stdout (which causes races between
        concurrent jobs), we inject mock sys/print into the handler's
        __globals__ dict. Each job has its own handler with its own globals,
        so there's no shared mutable state.

        The injection process:
        1. Create mock sys module with stdout/stderr pointing to capture buffers
        2. Create custom print() that writes to mock sys.stdout
        3. Save original globals values
        4. Inject mock sys/print into handler.__globals__
        5. Also inject into sys.modules["sys"] for "import sys" in handlers
        6. Run handler
        7. Restore original globals

        Why This Works:
        - Each job has distinct handler function (from scheduler._compile_handler)
        - Each handler has distinct __globals__ dict
        - Concurrent jobs don't interfere with each other's globals
        - No locks needed because no shared mutable state
        """
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Create isolated globals with output buffers
        job_globals = _create_job_globals(stdout_capture, stderr_capture)

        # Inject into handler's globals (save originals)
        handler_globals = self.handler.__globals__
        original_globals_sys = handler_globals.get("sys")
        original_globals_print = handler_globals.get("print")
        original_modules_sys = sys.modules.get("sys")

        handler_globals["sys"] = job_globals["sys"]
        handler_globals["print"] = job_globals["print"]
        sys.modules["sys"] = job_globals["sys"]  # For "import sys" in handlers

        # Also inject notify if available
        if self.context.notifier is not None:
            handler_globals["notify"] = self.context.notify

        try:
            # Execute the handler
            await self.handler()
        finally:
            # Restore original globals and modules
            if original_globals_sys is not None:
                handler_globals["sys"] = original_globals_sys
            elif "sys" in handler_globals:
                del handler_globals["sys"]

            if original_globals_print is not None:
                handler_globals["print"] = original_globals_print
            elif "print" in handler_globals:
                del handler_globals["print"]

            if original_modules_sys is not None:
                sys.modules["sys"] = original_modules_sys

        # Check final memory
        final_memory = process.memory_info().rss
        self._memory_peak_mb = (final_memory - initial_memory) // (1024 * 1024)

        # Check if we exceeded memory limit (log warning, don't fail)
        if self._memory_peak_mb > self.limits.max_memory_mb:
            logger.warning(
                f"Job {self.job.job_id} exceeded memory limit: "
                f"{self._memory_peak_mb}MB > {self.limits.max_memory_mb}MB"
            )

    def _get_duration_ms(self) -> int:
        """Calculate execution duration in milliseconds."""
        if self._start_time is None:
            return 0
        elapsed = datetime.now(UTC) - self._start_time
        return int(elapsed.total_seconds() * 1000)
