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
