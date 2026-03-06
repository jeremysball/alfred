"""Session storage for conversations (PRD #53).

Persistent session system with per-session folders containing
messages with embeddings. Supports both Telegram (thread ID as session)
and CLI (UUID sessions with /new, /resume).

File structure:
    data/sessions/
    ├── current.json             # CLI current session_id
    └── {session_id}/
        ├── meta.json            # Session metadata
        ├── current.jsonl        # Recent messages (loaded for context)
        └── archive.jsonl        # Older messages (post-compaction)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from src.session_storage import SessionStorage

logger = logging.getLogger(__name__)


SESSION_GAP_MINUTES = 30  # Default threshold for new session


def assign_session_id(
    new_message_time: datetime,
    last_message_time: datetime | None,
    current_session_id: str | None,
    threshold_minutes: int = SESSION_GAP_MINUTES,
) -> str:
    """Assign session ID based on time gap.

    Args:
        new_message_time: Timestamp of the new message
        last_message_time: Timestamp of previous message (None if no previous)
        current_session_id: Current session ID (None if no active session)
        threshold_minutes: Minutes of inactivity before new session

    Returns:
        Session ID to use for the new message
    """
    from uuid import uuid4

    logger.debug(f"assign_session_id called: current_session_id={current_session_id}, threshold={threshold_minutes}min")

    # No current session -> new session
    if current_session_id is None:
        new_session_id = f"sess_{uuid4().hex[:12]}"
        logger.debug(f"No current session, creating new session: {new_session_id}")
        return new_session_id

    # No last message time -> new session (conservative)
    if last_message_time is None:
        new_session_id = f"sess_{uuid4().hex[:12]}"
        logger.debug(f"No last message time, creating new session: {new_session_id}")
        return new_session_id

    # Calculate gap
    gap = (new_message_time - last_message_time).total_seconds() / 60
    logger.debug(f"Time gap since last message: {gap:.2f} minutes (threshold: {threshold_minutes}min)")

    # Clock skew (negative gap) -> new session
    if gap < 0:
        new_session_id = f"sess_{uuid4().hex[:12]}"
        logger.debug(f"Clock skew detected (negative gap: {gap:.2f}min), creating new session: {new_session_id}")
        return new_session_id

    # Gap exceeds threshold -> new session
    if gap > threshold_minutes:
        new_session_id = f"sess_{uuid4().hex[:12]}"
        logger.debug(f"Gap exceeds threshold ({gap:.2f}min > {threshold_minutes}min), creating new session: {new_session_id}")
        return new_session_id

    # Continue current session
    logger.debug(f"Continuing existing session: {current_session_id}")
    return current_session_id


class Role(Enum):
    """Message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ToolCallRecord:
    """Record of a tool call execution within a message.

    Attributes:
        tool_call_id: Unique identifier for this tool call
        tool_name: Name of the tool (e.g., "bash", "read")
        arguments: Dictionary of arguments passed to the tool
        output: Complete output from the tool execution
        status: Execution status ("success" or "error")
        insert_position: Character position in message.content where tool occurred
        sequence: Ordering when multiple tools at same position
    """

    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    output: str
    status: Literal["success", "error"]
    insert_position: int = 0
    sequence: int = 0


@dataclass
class Message:
    """Single exchange turn with optional embedding and token counts."""

    idx: int  # Position in file (local to current.jsonl or archive.jsonl)
    role: Role
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    embedding: list[float] | None = None
    input_tokens: int = 0  # Actual input tokens from LLM usage (for user messages)
    output_tokens: int = 0  # Actual output tokens from LLM usage (for assistant messages)
    cached_tokens: int = 0  # Cache read tokens from LLM usage
    reasoning_tokens: int = 0  # Reasoning tokens from LLM usage
    tool_calls: list[ToolCallRecord] | None = None  # Tool calls made during this message
    session_id: str = ""  # Session ID for grouping messages (PRD #76)


@dataclass
class SessionMeta:
    """Session metadata stored in meta.json."""

    session_id: str
    created_at: datetime
    last_active: datetime
    status: Literal["active", "idle"]
    current_count: int = 0  # Messages in current.jsonl
    archive_count: int = 0  # Messages in archive.jsonl
    # PRD #76: Session summarization tracking
    first_message_time: datetime | None = None  # Timestamp of first message
    last_summarized_count: int = 0  # Messages at last summary (0 = never summarized)
    summary_version: int = 0  # Summary regeneration counter (0 = no summary yet)

    @property
    def message_count(self) -> int:
        """Total messages across current and archive."""
        return self.current_count + self.archive_count


@dataclass
class SessionSummary:
    """Session summary stored in summary.json (PRD #76).

    Generated by cron job, stored per-session, replaced on regeneration.
    """

    id: str  # Unique summary ID (reused on regeneration)
    session_id: str  # Links to session folder
    timestamp: datetime  # When summary created
    message_range: tuple[int, int]  # (first_msg_idx, last_msg_idx)
    message_count: int  # How many messages summarized
    summary_text: str  # LLM-generated summary
    embedding: list[float] | None = None  # For semantic search
    version: int = 1  # Incremented on regeneration

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "message_range": list(self.message_range),  # Tuple -> list for JSON
            "message_count": self.message_count,
            "summary_text": self.summary_text,
            "embedding": self.embedding,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionSummary":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_range=(data["message_range"][0], data["message_range"][1]),  # List -> tuple
            message_count=data["message_count"],
            summary_text=data["summary_text"],
            embedding=data.get("embedding"),
            version=data.get("version", 1),
        )


@dataclass
class Session:
    """In-memory session with loaded messages."""

    meta: SessionMeta
    messages: list[Message] = field(default_factory=list)  # Loaded from current.jsonl


class SessionManager:
    """Singleton manager for CLI sessions.

    Persistent session tracking using SessionStorage.
    Supports both Telegram (thread ID as session) and CLI (UUID sessions).
    """

    _instance: SessionManager | None = None
    _storage: SessionStorage | None = None  # Set via initialize()
    _sessions: dict[str, Session] = {}  # Cache of loaded sessions
    _cli_session_id: str | None = None  # Current CLI session
    _local_sessions: dict[str, Session] = {}  # Instance-level cache

    def __new__(cls) -> SessionManager:
        """Prevent direct instantiation."""
        raise RuntimeError("Use SessionManager.get_instance()")

    @classmethod
    def initialize(cls, storage: SessionStorage) -> None:
        """Initialize with storage. Must be called before get_instance()."""
        cls._storage = storage
        # Load CLI current session if exists
        cls._cli_session_id = storage.get_cli_current()

    @classmethod
    def get_instance(cls) -> SessionManager:
        """Get or create singleton instance."""
        if cls._instance is None:
            if cls._storage is None:
                raise RuntimeError(
                    "SessionManager not initialized. Call initialize(storage) first."
                )
            # Create instance without calling __new__
            cls._instance = object.__new__(cls)
            cls._instance._local_sessions = {}  # Instance-level cache
        return cls._instance

    @property
    def storage(self) -> SessionStorage:
        """Get storage instance."""
        if SessionManager._storage is None:
            raise RuntimeError("SessionManager not initialized")
        return SessionManager._storage

    # === Session Lifecycle ===

    def get_or_create_session(self, session_id: str | None = None) -> Session:
        """Get existing session or create new one.

        For Telegram: session_id is the thread ID.
        For CLI: session_id is generated if not provided.
        """
        if session_id is None:
            # CLI mode - generate new session
            session_id = self.storage._generate_session_id()

        # Check cache first
        if session_id in self._local_sessions:
            return self._local_sessions[session_id]

        # Try to load from storage
        session = self.storage.load_session(session_id)
        if session is None:
            # Create new session
            meta = self.storage.create_session(session_id)
            session = Session(meta=meta, messages=[])

        self._local_sessions[session_id] = session
        return session

    def get_current_cli_session(self) -> Session | None:
        """Get current CLI session, loading from storage if needed."""
        if SessionManager._cli_session_id is None:
            return None
        return self.get_or_create_session(SessionManager._cli_session_id)

    def set_current_cli_session(self, session_id: str) -> None:
        """Set current CLI session."""
        SessionManager._cli_session_id = session_id
        self.storage.set_cli_current(session_id)

    def new_session(self) -> Session:
        """Create a new CLI session and set as current."""
        session = self.get_or_create_session()  # Generates new ID
        self.set_current_cli_session(session.meta.session_id)
        return session

    def resume_session(self, session_id: str) -> Session:
        """Resume an existing session."""
        if not self.storage.session_exists(session_id):
            raise ValueError(f"Session {session_id} not found")
        session = self.get_or_create_session(session_id)
        self.set_current_cli_session(session_id)
        return session

    def list_sessions(self) -> list[SessionMeta]:
        """List all sessions with metadata."""
        metas = []
        for session_id in self.storage.list_sessions():
            meta = self.storage.get_meta(session_id)
            if meta:
                metas.append(meta)
        # Sort by last_active descending
        metas.sort(key=lambda m: m.last_active, reverse=True)
        return metas

    # === Backwards-compatible API (for existing code) ===

    def start_session(self) -> Session:
        """Create new CLI session. Backwards-compatible."""
        return self.new_session()

    def add_message(self, role: str, content: str, session_id: str | None = None) -> None:
        """Append message to session.

        Args:
            role: "user", "assistant", or "system"
            content: Message content
            session_id: Optional session ID. If None, uses current CLI session.

        Raises:
            RuntimeError: If no active session exists
        """
        session: Session | None
        if session_id:
            # Telegram mode - get specific session
            session = self.get_or_create_session(session_id)
        else:
            # CLI mode - get current CLI session
            session = self.get_current_cli_session()
            if session is None:
                raise RuntimeError("No active session")

        role_enum = Role(role)
        idx = session.meta.current_count
        message = Message(
            idx=idx,
            role=role_enum,
            content=content,
            timestamp=datetime.now(UTC),
        )
        session.messages.append(message)
        session.meta.last_active = datetime.now(UTC)
        session.meta.current_count += 1

        # Persist to storage (spawn background task if event loop running)
        self._spawn_persist_task(session.meta.session_id, message)

    def get_session_messages(self, session_id: str | None = None) -> list[Message]:
        """Get all messages from a session.

        Args:
            session_id: Optional session ID. If None, uses current CLI session.

        Raises:
            RuntimeError: If no active session exists
        """
        session: Session | None
        if session_id:
            # Telegram mode - get specific session
            session = self.get_or_create_session(session_id)
            return list(session.messages)
        else:
            # CLI mode - get current CLI session
            session = self.get_current_cli_session()
            if session is None:
                raise RuntimeError("No active session")
            return list(session.messages)

    def get_messages(self) -> list[Message]:
        """Get all messages from current CLI session. Backwards-compatible."""
        return self.get_session_messages()

    def get_messages_for_context(self, session_id: str | None = None) -> list[tuple[str, str]]:
        """Get session messages formatted for context injection.

        Returns messages as (role, content) tuples, excluding the most
        recent user message (which is the current query being processed).

        Args:
            session_id: Optional session ID. If None, uses current CLI session.

        Returns:
            List of (role, content) tuples for session history.
        """
        if session_id:
            messages = self.get_session_messages(session_id)
        else:
            if not self.has_active_session():
                return []
            messages = self.get_messages()

        # Convert to (role, content) tuples, excluding the most recent user message
        result = []
        for msg in messages[:-1] if messages else []:  # Exclude last (current) message
            result.append((msg.role.value, msg.content))
        return result

    def get_messages_with_tools_for_context(self, session_id: str | None = None) -> list[Message]:
        """Get full session messages with tool_calls for context injection.

        Returns full Message objects (may have tool_calls attribute),
        excluding the most recent user message.

        Args:
            session_id: Optional session ID. If None, uses current CLI session.

        Returns:
            List of Message objects.
        """
        if session_id:
            messages = self.get_session_messages(session_id)
        else:
            if not self.has_active_session():
                return []
            messages = self.get_messages()

        # Return full message objects, excluding the most recent user message
        return list(messages[:-1] if messages else [])

    def _spawn_persist_task(self, session_id: str, message: Message) -> None:
        """Spawn background task to persist message (if event loop running)."""
        try:
            loop = asyncio.get_running_loop()
            # Get the session to save its meta (with updated counts)
            session = self._local_sessions.get(session_id)
            loop.create_task(self._persist_message(session_id, message, session))
        except RuntimeError:
            # No event loop running - message stays in memory
            # Will be persisted on next message or shutdown
            logger.debug(
                "could not find a running event loop. message stays in memory "
                "and will be persisted on next message or shutdown"
            )
            pass

    async def _persist_message(
        self, session_id: str, message: Message, session: Session | None = None
    ) -> None:
        """Persist message to storage and spawn embedding task."""
        await self.storage.append_message(session_id, message)
        # Save the in-memory meta (with updated counts) not stale disk version
        if session is not None:
            self.storage.save_meta(session.meta)
        # Spawn embedding task
        self.storage.spawn_embed_task(session_id, message.idx, message.content)

    def update_message_tokens(
        self,
        idx: int,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
        session_id: str | None = None,
    ) -> None:
        """Update token counts for a specific message.

        Args:
            idx: Message index (position in current.jsonl)
            input_tokens: Input token count to set
            output_tokens: Output token count to set
            cached_tokens: Cache read token count to set
            reasoning_tokens: Reasoning token count to set
            session_id: Optional session ID. If None, uses current CLI session.
        """
        session: Session | None
        if session_id:
            session = self.get_or_create_session(session_id)
        else:
            session = self.get_current_cli_session()
            if session is None:
                return

        # Find and update the message
        for msg in session.messages:
            if msg.idx == idx:
                msg.input_tokens = input_tokens
                msg.output_tokens = output_tokens
                msg.cached_tokens = cached_tokens
                msg.reasoning_tokens = reasoning_tokens
                break

        # Persist the updated token counts
        self._spawn_token_update_task(
            session.meta.session_id,
            idx,
            input_tokens,
            output_tokens,
            cached_tokens,
            reasoning_tokens,
        )

    def _spawn_token_update_task(
        self,
        session_id: str,
        idx: int,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
    ) -> None:
        """Spawn background task to persist token counts."""
        try:
            loop = asyncio.get_running_loop()
            # Token updates go to sidecar file (append-only, no race condition)
            loop.create_task(
                self.storage.update_message_tokens(
                    session_id,
                    idx,
                    input_tokens,
                    output_tokens,
                    cached_tokens,
                    reasoning_tokens,
                )
            )
        except RuntimeError:
            # No event loop running - will be persisted on next message
            pass

    def clear_session(self) -> None:
        """Clear current CLI session reference (doesn't delete)."""
        SessionManager._cli_session_id = None
        self._local_sessions.clear()

    def has_active_session(self) -> bool:
        """Check if there's an active CLI session."""
        return SessionManager._cli_session_id is not None
