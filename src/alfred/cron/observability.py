"""Structured logging for cron job execution.

Provides JSONL logging for audit and debugging of cron jobs.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Import ExecutionStatus locally to avoid circular import
def _get_status_success(status_value: str) -> bool:
    """Check if status is success without importing ExecutionStatus."""
    return status_value == "success"


class StructuredLogger:
    """Structured JSON logger for cron job execution.

    Writes log entries to a JSONL file for audit and debugging.
    """

    def __init__(self, log_file: Path) -> None:
        self.log_file = log_file
        self._lock = asyncio.Lock()

    async def _write_log(self, entry: dict[str, Any]) -> None:
        """Write a log entry to file."""
        async with self._lock:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")

    async def log_job_start(
        self,
        job_id: str,
        job_name: str,
        code_snapshot: str | None = None,
    ) -> None:
        """Log job execution start."""
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "INFO",
            "event": "job_start",
            "job_id": job_id,
            "job_name": job_name,
            "code_snapshot": code_snapshot,
        }
        await self._write_log(entry)
        logger.info(f"Job {job_name} ({job_id}) started")

    async def log_job_end(
        self,
        job_id: str,
        job_name: str,
        execution_record: Any,
        code_snapshot: str | None = None,
    ) -> None:
        """Log job execution end."""
        status = getattr(execution_record, "status", None)
        if status is not None and hasattr(status, "value"):
            status_value = status.value
        else:
            status_value = str(status) if status else "unknown"
        is_success = _get_status_success(status_value)
        level = "INFO" if is_success else "ERROR"
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "event": "job_end",
            "job_id": job_id,
            "job_name": job_name,
            "execution_id": getattr(execution_record, "execution_id", None),
            "status": status_value,
            "duration_ms": getattr(execution_record, "duration_ms", 0),
            "error_message": getattr(execution_record, "error_message", None),
            "stdout": getattr(execution_record, "stdout", None),
            "stderr": getattr(execution_record, "stderr", None),
            "code_snapshot": code_snapshot,
        }
        await self._write_log(entry)
        if is_success:
            logger.info(
                f"Job {job_name} ({job_id}) completed in "
                f"{getattr(execution_record, 'duration_ms', 0)}ms"
            )
        else:
            logger.error(
                f"Job {job_name} ({job_id}) failed: "
                f"{getattr(execution_record, 'error_message', 'unknown')}"
            )

    async def log_scheduler_event(self, event: str, message: str) -> None:
        """Log scheduler-level events (start, stop, etc.)."""
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "INFO",
            "event": event,
            "message": message,
        }
        await self._write_log(entry)
        logger.info(f"Scheduler event '{event}': {message}")

    async def log_warning(self, job_id: str | None, message: str) -> None:
        """Log a warning event."""
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "WARNING",
            "event": "warning",
            "job_id": job_id,
            "message": message,
        }
        await self._write_log(entry)
        logger.warning(message)
