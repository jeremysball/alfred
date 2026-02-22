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
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from src.session_storage import SessionStorage


class Role(Enum):
    """Message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Single exchange turn with optional embedding."""

    idx: int  # Position in file (local to current.jsonl or archive.jsonl)
    role: Role
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    embedding: list[float] | None = None


@dataclass
class SessionMeta:
    """Session metadata stored in meta.json."""

    session_id: str
    created_at: datetime
    last_active: datetime
    status: Literal["active", "idle"]
    current_count: int = 0  # Messages in current.jsonl
    archive_count: int = 0  # Messages in archive.jsonl

    @property
    def message_count(self) -> int:
        """Total messages across current and archive."""
        return self.current_count + self.archive_count


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

    def _spawn_persist_task(self, session_id: str, message: Message) -> None:
        """Spawn background task to persist message (if event loop running)."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._persist_message(session_id, message))
        except RuntimeError:
            # No event loop running - message stays in memory
            # Will be persisted on next message or shutdown
            pass

    async def _persist_message(self, session_id: str, message: Message) -> None:
        """Persist message to storage and spawn embedding task."""
        await self.storage.append_message(session_id, message)
        # Update meta
        meta = self.storage.get_meta(session_id)
        if meta:
            self.storage.save_meta(meta)
        # Spawn embedding task
        self.storage.spawn_embed_task(session_id, message.idx, message.content)

    def clear_session(self) -> None:
        """Clear current CLI session reference (doesn't delete)."""
        SessionManager._cli_session_id = None
        self._local_sessions.clear()

    def has_active_session(self) -> bool:
        """Check if there's an active CLI session."""
        return SessionManager._cli_session_id is not None
