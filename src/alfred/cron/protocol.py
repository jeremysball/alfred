"""Pydantic-based socket protocol for daemon communication.

Uses pydantic.dataclasses for validation on existing types.
Manual routing via match/case for type selection.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic.dataclasses import dataclass

if TYPE_CHECKING:
    from alfred.cron.models import ExecutionRecord, Job


# ============================================================================
# Pydantic Dataclass Wrappers (add validation to existing types)
# ============================================================================


@dataclass
class JobInfo:
    """Job info for socket transfer - wraps existing Job dataclass with validation."""

    job_id: str
    name: str
    expression: str
    code: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_run: datetime | None
    resource_limits: dict[str, object]
    chat_id: int | None
    # Computed fields added by daemon (must come after required fields)
    approved_at: datetime | None = None
    approved_by: str | None = None
    next_run: datetime | None = None
    is_overdue: bool = False
    run_count: int = 0

    @classmethod
    def from_job(cls, job: Job) -> JobInfo:
        """Convert existing Job dataclass to JobInfo with validation."""
        return cls(
            job_id=job.job_id,
            name=job.name,
            expression=job.expression,
            code=job.code,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            last_run=job.last_run,
            resource_limits=job.resource_limits.to_dict(),
            chat_id=job.chat_id,
        )


@dataclass
class ExecutionInfo:
    """Execution record for socket transfer - wraps ExecutionRecord dataclass."""

    execution_id: str
    job_id: str
    started_at: datetime
    ended_at: datetime
    status: str
    duration_ms: int
    error_message: str | None
    stdout: str | None
    stderr: str | None
    memory_peak_mb: int | None
    stdout_truncated: bool

    @classmethod
    def from_record(cls, record: ExecutionRecord) -> ExecutionInfo:
        """Convert existing ExecutionRecord dataclass to ExecutionInfo."""
        return cls(
            execution_id=record.execution_id,
            job_id=record.job_id,
            started_at=record.started_at,
            ended_at=record.ended_at,
            status=record.status.value,
            duration_ms=record.duration_ms,
            error_message=record.error_message,
            stdout=record.stdout,
            stderr=record.stderr,
            memory_peak_mb=record.memory_peak_mb,
            stdout_truncated=record.stdout_truncated,
        )


@dataclass
class JobFailureInfo:
    """Summary of recent job failures."""

    job_id: str
    job_name: str
    failed_at: datetime
    error_preview: str
    consecutive_failures: int


# ============================================================================
# Socket Messages (all use pydantic.dataclasses)
# ============================================================================


@dataclass
class Subscribe:
    """Subscribe to event notifications."""

    events: list[str]
    msg_type: Literal["subscribe"] = "subscribe"


@dataclass
class ListJobs:
    """Request list of all jobs."""

    status_filter: str | None = None
    msg_type: Literal["list_jobs"] = "list_jobs"


@dataclass
class SubmitJob:
    """Submit a new job for approval."""

    name: str
    expression: str
    code: str
    msg_type: Literal["submit_job"] = "submit_job"


@dataclass
class ApproveJob:
    """Approve a pending job."""

    job_identifier: str
    msg_type: Literal["approve_job"] = "approve_job"


@dataclass
class RejectJob:
    """Reject/delete a job."""

    job_identifier: str
    msg_type: Literal["reject_job"] = "reject_job"


@dataclass
class Ping:
    """Ping to check if daemon is alive."""

    msg_type: Literal["ping"] = "ping"


# ============================================================================
# Responses
# ============================================================================


@dataclass
class JobsResponse:
    """Response with job list."""

    jobs: list[JobInfo]
    recent_failures: list[JobFailureInfo]
    msg_type: Literal["jobs_response"] = "jobs_response"


@dataclass
class SubmitJobResponse:
    """Response to job submission."""

    success: bool
    job_id: str = ""
    message: str = ""
    msg_type: Literal["submit_job_response"] = "submit_job_response"


@dataclass
class ApproveJobResponse:
    """Response to job approval."""

    success: bool
    job_id: str = ""
    job_name: str = ""
    message: str = ""
    msg_type: Literal["approve_job_response"] = "approve_job_response"


@dataclass
class RejectJobResponse:
    """Response to job rejection."""

    success: bool
    job_id: str = ""
    job_name: str = ""
    message: str = ""
    msg_type: Literal["reject_job_response"] = "reject_job_response"


@dataclass
class Pong:
    """Ping response."""

    timestamp: datetime
    msg_type: Literal["pong"] = "pong"


# ============================================================================
# Events (one-way notifications)
# ============================================================================


@dataclass
class JobStarted:
    """Job execution started."""

    job_id: str
    job_name: str
    timestamp: datetime
    msg_type: Literal["job_started"] = "job_started"


@dataclass
class JobCompleted:
    """Job execution completed successfully."""

    job_id: str
    job_name: str
    duration_ms: int
    stdout_preview: str
    timestamp: datetime
    msg_type: Literal["job_completed"] = "job_completed"


@dataclass
class JobFailed:
    """Job execution failed."""

    job_id: str
    job_name: str
    error: str
    duration_ms: int
    timestamp: datetime
    msg_type: Literal["job_failed"] = "job_failed"


@dataclass
class Notification:
    """General notification (toast message)."""

    message: str
    timestamp: datetime
    level: Literal["info", "warning", "error"] = "info"
    msg_type: Literal["notification"] = "notification"


# ============================================================================
# Type Aliases
# ============================================================================

SocketMessage = (
    Subscribe
    | ListJobs
    | SubmitJob
    | ApproveJob
    | RejectJob
    | Ping
    | JobsResponse
    | SubmitJobResponse
    | ApproveJobResponse
    | RejectJobResponse
    | Pong
    | JobStarted
    | JobCompleted
    | JobFailed
    | Notification
)

ClientMessage = Subscribe | ListJobs | SubmitJob | ApproveJob | RejectJob | Ping
ServerMessage = (
    JobsResponse | SubmitJobResponse | ApproveJobResponse | RejectJobResponse | Pong | JobStarted | JobCompleted | JobFailed | Notification
)
Event = JobStarted | JobCompleted | JobFailed | Notification


# ============================================================================
# Serialization
# ============================================================================


def serialize_message(msg: SocketMessage) -> str:
    """Serialize a message to JSON string with newline delimiter."""
    import json
    from dataclasses import asdict
    from typing import cast

    def default(obj: object) -> object:
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Check for dataclass by looking for __dataclass_fields__
        dc_fields = getattr(obj, "__dataclass_fields__", None)
        if dc_fields is not None:
            # All SocketMessage types are dataclasses
            return asdict(cast(Any, obj))
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return json.dumps(asdict(cast(Any, msg)), default=default) + "\n"


def serialize_message_bytes(msg: SocketMessage) -> bytes:
    """Serialize a message to JSON bytes with newline delimiter."""
    return serialize_message(msg).encode("utf-8")


# ============================================================================
# Deserialization with Manual Routing
# ============================================================================


def parse_message(data: str | bytes) -> SocketMessage:
    """Parse JSON data into the appropriate message type using manual routing.

    Uses match/case for type selection. Validation happens via pydantic.dataclasses.
    """
    import json

    if isinstance(data, bytes):
        data = data.decode("utf-8")

    parsed = json.loads(data)
    msg_type = parsed.get("msg_type")

    if msg_type is None:
        raise ValueError(f"Message missing msg_type field: {data[:100]}")

    match msg_type:
        # Client -> Daemon
        case "subscribe":
            return Subscribe(**parsed)
        case "list_jobs":
            return ListJobs(**parsed)
        case "submit_job":
            return SubmitJob(**parsed)
        case "approve_job":
            return ApproveJob(**parsed)
        case "reject_job":
            return RejectJob(**parsed)
        case "ping":
            return Ping(**parsed)

        # Daemon -> Client (Responses)
        case "jobs_response":
            return _parse_jobs_response(parsed)
        case "submit_job_response":
            return SubmitJobResponse(**parsed)
        case "approve_job_response":
            return ApproveJobResponse(**parsed)
        case "reject_job_response":
            return RejectJobResponse(**parsed)
        case "pong":
            return _parse_pong(parsed)

        # Daemon -> Client (Events)
        case "job_started":
            return _parse_job_started(parsed)
        case "job_completed":
            return _parse_job_completed(parsed)
        case "job_failed":
            return _parse_job_failed(parsed)
        case "notification":
            return _parse_notification(parsed)

        case _:
            raise ValueError(f"Unknown message type: {msg_type}")


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO format datetime string."""
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _parse_jobs_response(parsed: dict[str, Any]) -> JobsResponse:
    """Parse JobsResponse with nested JobInfo objects."""
    jobs_data = parsed.get("jobs", [])
    failures_data = parsed.get("recent_failures", [])

    jobs = []
    for job_data in jobs_data:
        job_data["created_at"] = _parse_datetime(job_data["created_at"])
        job_data["updated_at"] = _parse_datetime(job_data["updated_at"])
        job_data["last_run"] = _parse_datetime(job_data.get("last_run"))
        job_data["approved_at"] = _parse_datetime(job_data.get("approved_at"))
        job_data["next_run"] = _parse_datetime(job_data.get("next_run"))
        jobs.append(JobInfo(**job_data))

    failures = []
    for failure_data in failures_data:
        failure_data["failed_at"] = _parse_datetime(failure_data.get("failed_at"))
        failures.append(JobFailureInfo(**failure_data))

    return JobsResponse(
        jobs=jobs,
        recent_failures=failures,
    )


def _parse_pong(parsed: dict[str, Any]) -> Pong:
    """Parse Pong with datetime."""
    return Pong(
        timestamp=_parse_datetime(parsed.get("timestamp")) or datetime.now(),
    )


def _parse_job_started(parsed: dict[str, Any]) -> JobStarted:
    """Parse JobStarted with datetime."""
    return JobStarted(
        job_id=parsed["job_id"],
        job_name=parsed["job_name"],
        timestamp=_parse_datetime(parsed.get("timestamp")) or datetime.now(),
    )


def _parse_job_completed(parsed: dict[str, Any]) -> JobCompleted:
    """Parse JobCompleted with datetime."""
    return JobCompleted(
        job_id=parsed["job_id"],
        job_name=parsed["job_name"],
        duration_ms=parsed["duration_ms"],
        stdout_preview=parsed.get("stdout_preview", ""),
        timestamp=_parse_datetime(parsed.get("timestamp")) or datetime.now(),
    )


def _parse_job_failed(parsed: dict[str, Any]) -> JobFailed:
    """Parse JobFailed with datetime."""
    return JobFailed(
        job_id=parsed["job_id"],
        job_name=parsed["job_name"],
        error=parsed["error"],
        duration_ms=parsed["duration_ms"],
        timestamp=_parse_datetime(parsed.get("timestamp")) or datetime.now(),
    )


def _parse_notification(parsed: dict[str, Any]) -> Notification:
    """Parse Notification with datetime."""
    return Notification(
        message=parsed["message"],
        timestamp=_parse_datetime(parsed.get("timestamp")) or datetime.now(),
        level=parsed.get("level", "info"),
    )


# ============================================================================
# Type Helpers
# ============================================================================


def is_event(msg: SocketMessage) -> bool:
    """Check if a message is a one-way event (not a request/response)."""
    return isinstance(msg, (JobStarted, JobCompleted, JobFailed, Notification))


def is_request(msg: SocketMessage) -> bool:
    """Check if a message is a client request that expects a response."""
    return isinstance(msg, (ListJobs, SubmitJob, ApproveJob, RejectJob, Ping))


def is_response(msg: SocketMessage) -> bool:
    """Check if a message is a response to a request."""
    return isinstance(
        msg,
        (JobsResponse, SubmitJobResponse, ApproveJobResponse, RejectJobResponse, Pong),
    )


def is_subscription(msg: SocketMessage) -> bool:
    """Check if a message is a subscription (no response expected)."""
    return isinstance(msg, Subscribe)
