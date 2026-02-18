"""In-memory session storage for CLI conversations (PRD #54).

Simple, single-session manager that maintains conversation history
in memory only. No persistence, no summarization—just raw message
history injected into context.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4


class Role(Enum):
    """Message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Single exchange turn."""

    role: Role
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Session:
    """In-memory conversation session."""

    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    messages: list[Message] = field(default_factory=list)


class SessionManager:
    """Singleton manager for the active CLI session.

    Stores messages in memory only. Creates session on demand
    when first message is added.
    """

    _instance: "SessionManager | None" = None
    _session: Session | None = None

    def __new__(cls) -> "SessionManager":
        """Prevent direct instantiation."""
        raise RuntimeError("Use SessionManager.get_instance()")

    @classmethod
    def get_instance(cls) -> "SessionManager":
        """Get or create singleton instance."""
        if cls._instance is None:
            # Create instance without calling __new__
            cls._instance = object.__new__(cls)
            cls._instance._session = None
        return cls._instance

    def start_session(self) -> Session:
        """Create new session. Clears any existing session."""
        self._session = Session()
        return self._session

    def add_message(self, role: str, content: str) -> None:
        """Append message to current session.

        Args:
            role: "user", "assistant", or "system"
            content: Message content

        Raises:
            RuntimeError: If no active session exists
        """
        if self._session is None:
            raise RuntimeError("No active session")

        role_enum = Role(role)
        message = Message(role=role_enum, content=content)
        self._session.messages.append(message)

    def get_messages(self) -> list[Message]:
        """Get all messages in chronological order.

        Raises:
            RuntimeError: If no active session exists
        """
        if self._session is None:
            raise RuntimeError("No active session")

        return list(self._session.messages)

    def clear_session(self) -> None:
        """Clear current session."""
        self._session = None

    def has_active_session(self) -> bool:
        """Check if there's an active session."""
        return self._session is not None
