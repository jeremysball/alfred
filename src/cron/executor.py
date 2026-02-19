"""Job execution with resource limits and monitoring.

The JobExecutor class wraps job execution with timeout enforcement,
memory monitoring, and output capture. It provides safe execution
of user-submitted code with configurable resource boundaries.
"""

import asyncio
import contextlib
import io
import logging
import tracemalloc
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psutil

from src.cron.models import ExecutionStatus, Job, ResourceLimits

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
    notifier: Any | None = None

    async def notify(self, message: str) -> None:
        """Send a notification to the user.

        Args:
            message: Message to send
        """
        if self.notifier:
            await self.notifier.send(message)

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


class JobExecutor:
    """Execute jobs with resource limits and monitoring.

    Provides:
    - Timeout enforcement via asyncio.wait_for
    - Memory usage tracking via psutil
    - Output capture with line limits
    - Safe execution namespace with injected globals
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
            handler: Compiled async handler function
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

        try:
            # Capture output
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            with (
                redirect_stdout(stdout_capture),
                redirect_stderr(stderr_capture),
            ):
                # Execute with timeout
                await self._execute_with_timeout()

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

    async def _execute_with_timeout(self) -> None:
        """Execute handler with timeout and memory monitoring."""
        # Create task for the handler
        task = asyncio.create_task(self._monitored_execution())

        try:
            await asyncio.wait_for(task, timeout=self.limits.timeout_seconds)
        except TimeoutError:
            # Cancel the task
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            raise

    async def _monitored_execution(self) -> None:
        """Execute handler while monitoring resources."""
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Execute the handler
        await self.handler()

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

    def _create_safe_globals(self) -> dict[str, Any]:
        """Create safe globals namespace for job execution.

        Returns:
            Dictionary of safe builtins and injected functions
        """
        return {
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
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "pow": pow,
                "divmod": divmod,
                "chr": chr,
                "ord": ord,
                "hex": hex,
                "bin": bin,
                "oct": oct,
                "format": format,
                "repr": repr,
                "sorted": sorted,
                "reversed": reversed,
                "any": any,
                "all": all,
                "hasattr": hasattr,
                "getattr": getattr,
                "setattr": setattr,
                "isinstance": isinstance,
                "issubclass": issubclass,
                "type": type,
                "Exception": Exception,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "IndexError": IndexError,
                "AttributeError": AttributeError,
                "RuntimeError": RuntimeError,
                "StopIteration": StopIteration,
                "GeneratorExit": GeneratorExit,
                "ArithmeticError": ArithmeticError,
                "LookupError": LookupError,
                "AssertionError": AssertionError,
                "BufferError": BufferError,
                "EOFError": EOFError,
                "FloatingPointError": FloatingPointError,
                "OSError": OSError,
                "ImportError": ImportError,
                "ModuleNotFoundError": ModuleNotFoundError,
                "NameError": NameError,
                "UnboundLocalError": UnboundLocalError,
                "BlockingIOError": BlockingIOError,
                "ChildProcessError": ChildProcessError,
                "ConnectionError": ConnectionError,
                "BrokenPipeError": BrokenPipeError,
                "ConnectionAbortedError": ConnectionAbortedError,
                "ConnectionRefusedError": ConnectionRefusedError,
                "ConnectionResetError": ConnectionResetError,
                "FileExistsError": FileExistsError,
                "FileNotFoundError": FileNotFoundError,
                "InterruptedError": InterruptedError,
                "IsADirectoryError": IsADirectoryError,
                "NotADirectoryError": NotADirectoryError,
                "PermissionError": PermissionError,
                "ProcessLookupError": ProcessLookupError,
                "TimeoutError": TimeoutError,
                "ReferenceError": ReferenceError,
                "SyntaxError": SyntaxError,
                "IndentationError": IndentationError,
                "TabError": TabError,
                "SystemError": SystemError,
                "UnicodeError": UnicodeError,
                "UnicodeDecodeError": UnicodeDecodeError,
                "UnicodeEncodeError": UnicodeEncodeError,
                "UnicodeTranslateError": UnicodeTranslateError,
                "Warning": Warning,
                "UserWarning": UserWarning,
                "DeprecationWarning": DeprecationWarning,
                "PendingDeprecationWarning": PendingDeprecationWarning,
                "SyntaxWarning": SyntaxWarning,
                "RuntimeWarning": RuntimeWarning,
                "FutureWarning": FutureWarning,
                "ImportWarning": ImportWarning,
                "UnicodeWarning": UnicodeWarning,
                "BytesWarning": BytesWarning,
                "ResourceWarning": ResourceWarning,
            },
            "notify": self.context.notify,
            "store_get": self.context.store_get,
            "store_set": self.context.store_set,
        }
