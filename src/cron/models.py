"""Data models for cron scheduler.

Job and ExecutionRecord dataclasses for persistence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class JobStatus(Enum):
    """Job execution status."""

    ACTIVE = "active"
    PENDING = "pending"
    PAUSED = "paused"


class ExecutionStatus(Enum):
    """Job execution result status."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class Job:
    """Cron job definition.

    Contains all data needed to persist and recreate a job.
    The code field contains the Python source code as a string,
    which will be compiled at load time.
    """

    job_id: str
    name: str
    expression: str  # Cron expression like "*/5 * * * *"
    code: str  # Python code as string: "async def run(): ..."
    status: str = "active"  # "active", "pending", "paused"
    last_run: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    updated_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "name": self.name,
            "expression": self.expression,
            "code": self.code,
            "status": self.status,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def _parse_datetime(cls, value: str | None) -> datetime:
        """Parse datetime from string, defaulting to now if empty."""
        if value:
            return datetime.fromisoformat(value)
        return datetime.now().astimezone()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        """Create Job from dictionary (JSON deserialization)."""
        return cls(
            job_id=data["job_id"],
            name=data["name"],
            expression=data["expression"],
            code=data["code"],
            status=data.get("status", "active"),
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            created_at=cls._parse_datetime(data.get("created_at")),
            updated_at=cls._parse_datetime(data.get("updated_at")),
        )


@dataclass
class ExecutionRecord:
    """Record of a single job execution.

    Stored in cron_history.jsonl for audit and debugging.
    """

    execution_id: str
    job_id: str
    started_at: datetime
    ended_at: datetime
    status: ExecutionStatus
    duration_ms: int
    error_message: str | None = None
    stdout: str | None = None
    stderr: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert execution record to dictionary for JSON serialization."""
        return {
            "execution_id": self.execution_id,
            "job_id": self.job_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionRecord":
        """Create ExecutionRecord from dictionary (JSON deserialization)."""
        return cls(
            execution_id=data["execution_id"],
            job_id=data["job_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"]),
            status=ExecutionStatus(data["status"]),
            duration_ms=data["duration_ms"],
            error_message=data.get("error_message"),
            stdout=data.get("stdout"),
            stderr=data.get("stderr"),
        )
