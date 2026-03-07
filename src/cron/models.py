"""Data models for cron scheduler.

Job and ExecutionRecord dataclasses for persistence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.type_defs import JsonObject, ensure_json_object


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


def _require_str(data: JsonObject, key: str) -> str:
    value = data.get(key)
    if isinstance(value, str):
        return value
    raise ValueError(f"Missing or invalid {key}")


def _get_int(data: JsonObject, key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return default


def _get_bool(data: JsonObject, key: str, default: bool) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    return default


def _get_optional_str(data: JsonObject, key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def _get_optional_int(data: JsonObject, key: str) -> int | None:
    value = data.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


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

    def to_dict(self) -> JsonObject:
        """Convert limits to dictionary for JSON serialization."""
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
            "allow_network": self.allow_network,
            "max_output_lines": self.max_output_lines,
        }

    @classmethod
    def from_dict(cls, data: JsonObject) -> "ResourceLimits":
        """Create ResourceLimits from dictionary."""
        return cls(
            timeout_seconds=_get_int(data, "timeout_seconds", 30),
            max_memory_mb=_get_int(data, "max_memory_mb", 100),
            allow_network=_get_bool(data, "allow_network", False),
            max_output_lines=_get_int(data, "max_output_lines", 1000),
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
    handler_id: str | None = None  # System job handler identifier

    def to_dict(self) -> JsonObject:
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
            "handler_id": self.handler_id,
        }

    @classmethod
    def _parse_datetime(cls, value: str | None) -> datetime:
        """Parse datetime from string, defaulting to now if empty."""
        if value:
            return datetime.fromisoformat(value)
        return datetime.now().astimezone()

    @classmethod
    def from_dict(cls, data: JsonObject) -> "Job":
        """Create Job from dictionary (JSON deserialization)."""
        limits_value = data.get("resource_limits", {})
        limits_data = ensure_json_object(limits_value) if isinstance(limits_value, dict) else {}
        resource_limits = ResourceLimits.from_dict(limits_data) if limits_data else ResourceLimits()

        last_run_value = data.get("last_run")
        last_run = (
            datetime.fromisoformat(last_run_value)
            if isinstance(last_run_value, str)
            else None
        )

        created_at = cls._parse_datetime(_get_optional_str(data, "created_at"))
        updated_at = cls._parse_datetime(_get_optional_str(data, "updated_at"))

        return cls(
            job_id=_require_str(data, "job_id"),
            name=_require_str(data, "name"),
            expression=_require_str(data, "expression"),
            code=_require_str(data, "code"),
            status=_get_optional_str(data, "status") or "active",
            last_run=last_run,
            created_at=created_at,
            updated_at=updated_at,
            resource_limits=resource_limits,
            chat_id=_get_optional_int(data, "chat_id"),
            handler_id=_get_optional_str(data, "handler_id"),
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

    def to_dict(self) -> JsonObject:
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
    def from_dict(cls, data: JsonObject) -> "ExecutionRecord":
        """Create ExecutionRecord from dictionary (JSON deserialization)."""
        started_at = datetime.fromisoformat(_require_str(data, "started_at"))
        ended_at = datetime.fromisoformat(_require_str(data, "ended_at"))
        status_value = _require_str(data, "status")

        return cls(
            execution_id=_require_str(data, "execution_id"),
            job_id=_require_str(data, "job_id"),
            started_at=started_at,
            ended_at=ended_at,
            status=ExecutionStatus(status_value),
            duration_ms=_get_int(data, "duration_ms", 0),
            error_message=_get_optional_str(data, "error_message"),
            stdout=_get_optional_str(data, "stdout"),
            stderr=_get_optional_str(data, "stderr"),
            memory_peak_mb=_get_optional_int(data, "memory_peak_mb"),
            stdout_truncated=_get_bool(data, "stdout_truncated", False),
        )
