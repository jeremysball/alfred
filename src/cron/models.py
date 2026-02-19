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
class ResourceLimits:
    """Resource limits for job execution.

    Defines boundaries for CPU time, memory, network, and output.
    Used by JobExecutor to enforce safe execution of user code.
    """

    timeout_seconds: int = 30
    max_memory_mb: int = 100
    allow_network: bool = False
    max_output_lines: int = 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert limits to dictionary for JSON serialization."""
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
            "allow_network": self.allow_network,
            "max_output_lines": self.max_output_lines,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResourceLimits":
        """Create ResourceLimits from dictionary."""
        return cls(
            timeout_seconds=data.get("timeout_seconds", 30),
            max_memory_mb=data.get("max_memory_mb", 100),
            allow_network=data.get("allow_network", False),
            max_output_lines=data.get("max_output_lines", 1000),
        )


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
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    chat_id: int | None = None  # Telegram chat_id for job notifications
    sandbox_enabled: bool = False  # Whether to use restricted builtins
    error_message: str | None = None  # Error message if job failed to load

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
            "resource_limits": self.resource_limits.to_dict(),
            "chat_id": self.chat_id,
            "sandbox_enabled": self.sandbox_enabled,
            "error_message": self.error_message,
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
        limits_data = data.get("resource_limits", {})
        resource_limits = ResourceLimits.from_dict(limits_data) if limits_data else ResourceLimits()

        return cls(
            job_id=data["job_id"],
            name=data["name"],
            expression=data["expression"],
            code=data["code"],
            status=data.get("status", "active"),
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            created_at=cls._parse_datetime(data.get("created_at")),
            updated_at=cls._parse_datetime(data.get("updated_at")),
            resource_limits=resource_limits,
            chat_id=data.get("chat_id"),
            sandbox_enabled=data.get("sandbox_enabled", False),
            error_message=data.get("error_message"),
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
    memory_peak_mb: int | None = None
    stdout_truncated: bool = False

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
            "memory_peak_mb": self.memory_peak_mb,
            "stdout_truncated": self.stdout_truncated,
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
            memory_peak_mb=data.get("memory_peak_mb"),
            stdout_truncated=data.get("stdout_truncated", False),
        )
