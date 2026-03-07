"""Socket protocol for cron runner <-> TUI communication.

Defines message types and serialization for the Unix socket interface.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Literal

logger = logging.getLogger(__name__)

# Socket path (XDG cache directory)
SOCKET_NAME = "notify.sock"


class MessageType(StrEnum):
    """Types of messages sent over the socket."""

    # Notifications (show as toast)
    NOTIFY = "notify"

    # Job lifecycle events
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"

    # Runner lifecycle events
    RUNNER_STARTED = "runner_started"
    RUNNER_STOPPING = "runner_stopping"

    # Control messages
    PING = "ping"
    PONG = "pong"

    # Query/Request-Response for live data
    QUERY_JOBS = "query_jobs"
    QUERY_JOBS_RESPONSE = "query_jobs_response"
    
    # Job management commands (request-response)
    SUBMIT_JOB = "submit_job"
    SUBMIT_JOB_RESPONSE = "submit_job_response"
    APPROVE_JOB = "approve_job"
    APPROVE_JOB_RESPONSE = "approve_job_response"
    REJECT_JOB = "reject_job"
    REJECT_JOB_RESPONSE = "reject_job_response"


@dataclass
class SocketMessage:
    """Base message sent over the socket.

    All messages are JSON-serialized with a trailing newline.
    """

    type: MessageType
    timestamp: datetime = field(default_factory=datetime.now)

    def to_json(self) -> str:
        """Serialize message to JSON string with newline delimiter."""
        data = asdict(self)
        data["type"] = self.type.value
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data) + "\n"

    @classmethod
    def from_json(cls, data: str) -> "SocketMessage":
        """Deserialize message from JSON string."""
        obj = json.loads(data)
        obj["type"] = MessageType(obj["type"])
        obj["timestamp"] = datetime.fromisoformat(obj["timestamp"])

        # Dispatch to correct subclass
        msg_type = obj.pop("type")
        if msg_type == MessageType.NOTIFY:
            return NotifyMessage(**obj)
        elif msg_type == MessageType.JOB_STARTED:
            return JobStartedMessage(**obj)
        elif msg_type == MessageType.JOB_COMPLETED:
            return JobCompletedMessage(**obj)
        elif msg_type == MessageType.JOB_FAILED:
            return JobFailedMessage(**obj)
        elif msg_type == MessageType.RUNNER_STARTED:
            return RunnerStartedMessage(**obj)
        elif msg_type == MessageType.RUNNER_STOPPING:
            return RunnerStoppingMessage(**obj)
        elif msg_type == MessageType.PING:
            return PingMessage(**obj)
        elif msg_type == MessageType.PONG:
            return PongMessage(**obj)
        elif msg_type == MessageType.QUERY_JOBS:
            return QueryJobsRequest(**obj)
        elif msg_type == MessageType.QUERY_JOBS_RESPONSE:
            return QueryJobsResponse(**obj)
        elif msg_type == MessageType.SUBMIT_JOB:
            return SubmitJobRequest(**obj)
        elif msg_type == MessageType.SUBMIT_JOB_RESPONSE:
            return SubmitJobResponse(**obj)
        elif msg_type == MessageType.APPROVE_JOB:
            return ApproveJobRequest(**obj)
        elif msg_type == MessageType.APPROVE_JOB_RESPONSE:
            return ApproveJobResponse(**obj)
        elif msg_type == MessageType.REJECT_JOB:
            return RejectJobRequest(**obj)
        elif msg_type == MessageType.REJECT_JOB_RESPONSE:
            return RejectJobResponse(**obj)
        else:
            raise ValueError(f"Unknown message type: {msg_type}")


@dataclass
class NotifyMessage(SocketMessage):
    """Show a toast notification in the TUI."""

    type: MessageType = field(default=MessageType.NOTIFY, init=False)
    message: str = ""
    level: Literal["info", "warning", "error"] = "info"


@dataclass
class JobStartedMessage(SocketMessage):
    """Job has started executing."""

    type: MessageType = field(default=MessageType.JOB_STARTED, init=False)
    job_id: str = ""
    job_name: str = ""


@dataclass
class JobCompletedMessage(SocketMessage):
    """Job has completed successfully."""

    type: MessageType = field(default=MessageType.JOB_COMPLETED, init=False)
    job_id: str = ""
    job_name: str = ""
    duration_ms: int = 0
    stdout_preview: str = ""  # First 200 chars of output


@dataclass
class JobFailedMessage(SocketMessage):
    """Job has failed with an error."""

    type: MessageType = field(default=MessageType.JOB_FAILED, init=False)
    job_id: str = ""
    job_name: str = ""
    error: str = ""
    duration_ms: int = 0


@dataclass
class RunnerStartedMessage(SocketMessage):
    """Cron runner has started."""

    type: MessageType = field(default=MessageType.RUNNER_STARTED, init=False)
    pid: int = 0


@dataclass
class RunnerStoppingMessage(SocketMessage):
    """Cron runner is shutting down."""

    type: MessageType = field(default=MessageType.RUNNER_STOPPING, init=False)
    reason: str = "shutdown"


@dataclass
class PingMessage(SocketMessage):
    """Ping to check if TUI is alive."""

    type: MessageType = field(default=MessageType.PING, init=False)


@dataclass
class PongMessage(SocketMessage):
    """Pong response to ping."""

    type: MessageType = field(default=MessageType.PONG, init=False)


@dataclass
class QueryJobsRequest(SocketMessage):
    """Request current job status from daemon."""

    type: MessageType = field(default=MessageType.QUERY_JOBS, init=False)
    request_id: str = ""


@dataclass
class QueryJobsResponse(SocketMessage):
    """Current job statuses and recent executions."""

    type: MessageType = field(default=MessageType.QUERY_JOBS_RESPONSE, init=False)
    request_id: str = ""
    jobs: list = field(default_factory=list)
    recent_failures: list = field(default_factory=list)


# Job Management Messages


@dataclass
class SubmitJobRequest(SocketMessage):
    """Submit a new job for approval."""

    type: MessageType = field(default=MessageType.SUBMIT_JOB, init=False)
    request_id: str = ""
    name: str = ""
    expression: str = ""
    code: str = ""


@dataclass
class SubmitJobResponse(SocketMessage):
    """Response to job submission."""

    type: MessageType = field(default=MessageType.SUBMIT_JOB_RESPONSE, init=False)
    request_id: str = ""
    success: bool = False
    job_id: str = ""
    message: str = ""


@dataclass
class ApproveJobRequest(SocketMessage):
    """Approve a pending job."""

    type: MessageType = field(default=MessageType.APPROVE_JOB, init=False)
    request_id: str = ""
    job_identifier: str = ""  # ID or name


@dataclass
class ApproveJobResponse(SocketMessage):
    """Response to job approval."""

    type: MessageType = field(default=MessageType.APPROVE_JOB_RESPONSE, init=False)
    request_id: str = ""
    success: bool = False
    job_id: str = ""
    job_name: str = ""
    message: str = ""


@dataclass
class RejectJobRequest(SocketMessage):
    """Reject/delete a job."""

    type: MessageType = field(default=MessageType.REJECT_JOB, init=False)
    request_id: str = ""
    job_identifier: str = ""  # ID or name


@dataclass
class RejectJobResponse(SocketMessage):
    """Response to job rejection."""

    type: MessageType = field(default=MessageType.REJECT_JOB_RESPONSE, init=False)
    request_id: str = ""
    success: bool = False
    job_id: str = ""
    job_name: str = ""
    message: str = ""
