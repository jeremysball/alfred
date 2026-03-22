"""Unified session manager using SQLiteStore (PRD #109 M2/M5).

Replaces SessionStorage with SQLiteStore for persistence.
Uses dependency injection - not a singleton.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from alfred.storage.sqlite import SQLiteStore
from alfred.utils import run_async

logger = logging.getLogger(__name__)


class Role(Enum):
    """Message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ToolCallRecord:
    """Record of a tool call execution within a message."""

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

    idx: int
    role: Role
    content: str
    id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    embedding: list[float] | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    reasoning_content: str = ""  # Persisted reasoning/thinking content
    tool_calls: list[ToolCallRecord] | None = None
    streaming: bool = False


@dataclass
class SessionMeta:
    """Session metadata."""

    session_id: str
    created_at: datetime
    last_active: datetime
    status: Literal["active", "idle"]
    message_count: int = 0
    # PRD #76: Session summarization tracking
    first_message_time: datetime | None = None
    last_summarized_count: int = 0
    summary_version: int = 0


@dataclass
class Session:
    """In-memory session with loaded messages."""

    meta: SessionMeta
    messages: list[Message] = field(default_factory=list)


class SessionManager:
    """Session manager using SQLiteStore for persistence.

    Uses dependency injection - create with explicit dependencies:
        manager = SessionManager(store=sqlite_store, data_dir=data_dir)

    For global access, register in ServiceLocator:
        from alfred.container import ServiceLocator
        ServiceLocator.register(SessionManager, manager)
        # Later: ServiceLocator.resolve(SessionManager)
    """

    def __init__(self, store: SQLiteStore, data_dir: Path) -> None:
        """Initialize session manager with explicit dependencies.

        Args:
            store: SQLiteStore instance for persistence
            data_dir: Data directory for current.json file
        """
        self._store = store
        self._data_dir = data_dir
        self._sessions: dict[str, Session] = {}
        self._cli_session_id: str | None = None

        # Load CLI current session
        self._load_cli_current()

    def _load_cli_current(self) -> None:
        """Load CLI current session from file."""
        current_file = self._data_dir / "sessions" / "current.json"
        if current_file.exists():
            try:
                data = json.loads(current_file.read_text())
                self._cli_session_id = data.get("session_id")
            except Exception:
                pass

    def _save_cli_current(self) -> None:
        """Save CLI current session to file."""
        if self._cli_session_id is None:
            return
        current_file = self._data_dir / "sessions" / "current.json"
        current_file.parent.mkdir(parents=True, exist_ok=True)
        current_file.write_text(json.dumps({"session_id": self._cli_session_id}))

    @property
    def store(self) -> SQLiteStore:
        """Get SQLiteStore instance."""
        return self._store

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return str(uuid.uuid4())

    def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        try:
            result = run_async(self.store.load_session(session_id))
            return result is not None
        except Exception:
            return False

    async def session_exists_async(self, session_id: str) -> bool:
        """Check if session exists (async version)."""
        try:
            result = await self.store.load_session(session_id)
            return result is not None
        except Exception:
            return False

    def get_or_create_session(self, session_id: str | None = None) -> Session:
        """Get existing session or create new one."""
        if session_id is None:
            session_id = self._generate_session_id()

        # Check cache
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try to load from store
        try:
            data = run_async(self.store.load_session(session_id))
            return self._create_session_from_data(session_id, data)
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            # Create new session on error
            meta = SessionMeta(
                session_id=session_id,
                created_at=datetime.now(UTC),
                last_active=datetime.now(UTC),
                status="active",
            )
            return Session(meta=meta, messages=[])

    async def get_or_create_session_async(self, session_id: str | None = None) -> Session:
        """Get existing session or create new one (async version)."""
        if session_id is None:
            session_id = self._generate_session_id()

        # Check cache
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try to load from store
        try:
            data = await self.store.load_session(session_id)
            return self._create_session_from_data(session_id, data)
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            # Create new session on error
            meta = SessionMeta(
                session_id=session_id,
                created_at=datetime.now(UTC),
                last_active=datetime.now(UTC),
                status="active",
            )
            return Session(meta=meta, messages=[])

    def _create_session_from_data(self, session_id: str, data: dict[str, Any] | None) -> Session:
        """Create Session object from stored data."""
        if data:
            # Parse messages
            messages = []
            for msg_data in data.get("messages", []):
                # Convert dict tool_calls to ToolCallRecord objects
                tool_calls_data = msg_data.get("tool_calls")
                tool_calls = None
                if tool_calls_data:
                    tool_calls = [
                        ToolCallRecord(
                            tool_call_id=tc["tool_call_id"],
                            tool_name=tc["tool_name"],
                            arguments=tc.get("arguments", {}),
                            output=tc.get("output", ""),
                            status=tc.get("status", "success"),
                            insert_position=tc.get("insert_position", 0),
                            sequence=tc.get("sequence", 0),
                        )
                        for tc in tool_calls_data
                    ]

                # Handle timestamp - older sessions may not have it
                timestamp_str = msg_data.get("timestamp")
                if timestamp_str:
                    try:
                        msg_timestamp = datetime.fromisoformat(timestamp_str)
                    except (ValueError, TypeError):
                        msg_timestamp = datetime.now(UTC)
                else:
                    msg_timestamp = datetime.now(UTC)

                msg = Message(
                    idx=msg_data.get("idx", 0),
                    role=Role(msg_data["role"]),
                    content=msg_data["content"],
                    id=str(msg_data.get("id") or msg_data.get("idx", 0)),
                    timestamp=msg_timestamp,
                    embedding=msg_data.get("embedding"),
                    input_tokens=msg_data.get("input_tokens", 0),
                    output_tokens=msg_data.get("output_tokens", 0),
                    cached_tokens=msg_data.get("cached_tokens", 0),
                    reasoning_tokens=msg_data.get("reasoning_tokens", 0),
                    reasoning_content=msg_data.get("reasoning_content", ""),
                    tool_calls=tool_calls,
                    streaming=bool(msg_data.get("streaming", False)),
                )
                messages.append(msg)

            meta = SessionMeta(
                session_id=session_id,
                created_at=datetime.fromisoformat(data.get("created_at", datetime.now(UTC).isoformat())),
                last_active=datetime.fromisoformat(data.get("updated_at", datetime.now(UTC).isoformat())),
                status="active",
                message_count=len(messages),
            )
            session = Session(meta=meta, messages=messages)
        else:
            # Create new session
            meta = SessionMeta(
                session_id=session_id,
                created_at=datetime.now(UTC),
                last_active=datetime.now(UTC),
                status="active",
            )
            session = Session(meta=meta, messages=[])

        self._sessions[session_id] = session
        return session

    def get_current_cli_session(self) -> Session | None:
        """Get current CLI session."""
        if self._cli_session_id is None:
            return None
        return self.get_or_create_session(self._cli_session_id)

    async def get_current_cli_session_async(self) -> Session | None:
        """Get current CLI session (async version)."""
        if self._cli_session_id is None:
            return None
        return await self.get_or_create_session_async(self._cli_session_id)

    def set_current_cli_session(self, session_id: str) -> None:
        """Set current CLI session."""
        self._cli_session_id = session_id
        self._save_cli_current()

    def new_session(self) -> Session:
        """Create new CLI session."""
        session = self.get_or_create_session()
        self.set_current_cli_session(session.meta.session_id)
        return session

    async def new_session_async(self) -> Session:
        """Create new CLI session (async version)."""
        session = await self.get_or_create_session_async()
        self.set_current_cli_session(session.meta.session_id)
        return session

    def resume_session(self, session_id: str) -> Session:
        """Resume existing session."""
        if not self.session_exists(session_id):
            raise ValueError(f"Session {session_id} not found")
        session = self.get_or_create_session(session_id)
        self.set_current_cli_session(session_id)
        return session

    async def resume_session_async(self, session_id: str) -> Session:
        """Resume existing session (async version)."""
        if not await self.session_exists_async(session_id):
            raise ValueError(f"Session {session_id} not found")
        session = await self.get_or_create_session_async(session_id)
        self.set_current_cli_session(session_id)
        return session

    def list_sessions(self) -> list[SessionMeta]:
        """List all sessions."""
        try:
            sessions_data = run_async(self.store.list_sessions(limit=1000))

            metas = []
            for data in sessions_data:
                meta = SessionMeta(
                    session_id=data["session_id"],
                    created_at=datetime.fromisoformat(data.get("created_at", datetime.now(UTC).isoformat())),
                    last_active=datetime.fromisoformat(data.get("updated_at", datetime.now(UTC).isoformat())),
                    status="active",
                    message_count=len(data.get("messages", [])),
                )
                metas.append(meta)

            # Sort by last_active descending
            metas.sort(key=lambda m: m.last_active, reverse=True)
            return metas

        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    async def list_sessions_async(self) -> list[SessionMeta]:
        """List all sessions (async version)."""
        try:
            sessions_data = await self.store.list_sessions(limit=1000)

            metas = []
            for data in sessions_data:
                meta = SessionMeta(
                    session_id=data["session_id"],
                    created_at=datetime.fromisoformat(data.get("created_at", datetime.now(UTC).isoformat())),
                    last_active=datetime.fromisoformat(data.get("updated_at", datetime.now(UTC).isoformat())),
                    status="active",
                    message_count=len(data.get("messages", [])),
                )
                metas.append(meta)

            # Sort by last_active descending
            metas.sort(key=lambda m: m.last_active, reverse=True)
            return metas

        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    def start_session(self) -> Session:
        """Create new CLI session (backwards-compatible)."""
        return self.new_session()

    def add_message(self, role: str, content: str, session_id: str | None = None) -> None:
        """Append message to session."""
        session: Session | None
        if session_id:
            session = self.get_or_create_session(session_id)
        else:
            session = self.get_current_cli_session()
            if session is None:
                raise RuntimeError("No active session")

        role_enum = Role(role)
        idx = len(session.messages)
        message = Message(
            idx=idx,
            role=role_enum,
            content=content,
            id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC),
        )
        session.messages.append(message)
        session.meta.last_active = datetime.now(UTC)
        session.meta.message_count = len(session.messages)

        # Persist
        self._spawn_persist_task(session.meta.session_id, session.messages)

    def get_session_messages(self, session_id: str | None = None) -> list[Message]:
        """Get all messages from a session."""
        session: Session | None
        if session_id:
            session = self.get_or_create_session(session_id)
            return list(session.messages)
        else:
            session = self.get_current_cli_session()
            if session is None:
                raise RuntimeError("No active session")
            return list(session.messages)

    def get_messages(self) -> list[Message]:
        """Get messages from current CLI session."""
        return self.get_session_messages()

    def get_messages_for_context(self, session_id: str | None = None) -> list[tuple[str, str]]:
        """Get messages formatted for context injection."""
        if session_id:
            messages = self.get_session_messages(session_id)
        else:
            if not self.has_active_session():
                return []
            messages = self.get_messages()

        result = []
        for msg in messages[:-1] if messages else []:
            result.append((msg.role.value, msg.content))
        return result

    def get_messages_with_tools_for_context(self, session_id: str | None = None) -> list[Message]:
        """Get full messages with tool_calls for context injection."""
        if session_id:
            messages = self.get_session_messages(session_id)
        else:
            if not self.has_active_session():
                return []
            messages = self.get_messages()
        return list(messages[:-1] if messages else [])

    def _spawn_persist_task(self, session_id: str, messages: list[Message]) -> None:
        """Spawn background task to persist messages."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._persist_messages(session_id, messages))
        except RuntimeError:
            # No event loop - persist synchronously
            asyncio.run(self._persist_messages(session_id, messages))

    async def _persist_messages(self, session_id: str, messages: list[Message]) -> None:
        """Persist messages to SQLiteStore."""
        try:
            messages_data: list[dict[str, Any]] = []
            for msg in messages:
                msg_dict: dict[str, Any] = {
                    "idx": msg.idx,
                    "id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "input_tokens": msg.input_tokens,
                    "output_tokens": msg.output_tokens,
                    "cached_tokens": msg.cached_tokens,
                    "reasoning_tokens": msg.reasoning_tokens,
                    "reasoning_content": msg.reasoning_content,
                    "streaming": msg.streaming,
                }
                if msg.embedding:
                    msg_dict["embedding"] = msg.embedding
                if msg.tool_calls:
                    # tool_calls are always ToolCallRecord objects (converted at load edge)
                    msg_dict["tool_calls"] = [
                        {
                            "tool_call_id": tc.tool_call_id,
                            "tool_name": tc.tool_name,
                            "arguments": tc.arguments,
                            "output": tc.output,
                            "status": tc.status,
                            "insert_position": tc.insert_position,
                            "sequence": tc.sequence,
                        }
                        for tc in msg.tool_calls
                    ]
                messages_data.append(msg_dict)

            await self.store.save_session(session_id, messages_data)
        except Exception as e:
            logger.error(f"Error persisting session {session_id}: {e}")

    def update_message_tokens(
        self,
        idx: int,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
        session_id: str | None = None,
    ) -> None:
        """Update token counts for a message."""
        session: Session | None
        if session_id:
            session = self.get_or_create_session(session_id)
        else:
            session = self.get_current_cli_session()
            if session is None:
                return

        for msg in session.messages:
            if msg.idx == idx:
                msg.input_tokens = input_tokens
                msg.output_tokens = output_tokens
                msg.cached_tokens = cached_tokens
                msg.reasoning_tokens = reasoning_tokens
                break

        # Re-persist
        self._spawn_persist_task(session.meta.session_id, session.messages)

    def clear_session(self) -> None:
        """Clear current CLI session reference."""
        self._cli_session_id = None
        self._sessions.clear()

    def has_active_session(self) -> bool:
        """Check if there's an active CLI session."""
        return self._cli_session_id is not None
