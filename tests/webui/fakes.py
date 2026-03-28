"""Shared Web UI test fakes.

Use real production dataclasses for session, message, tool-call, and token state.
Keep these fakes small and explicit.
Do not add bare root-level MagicMock Alfred fixtures here.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from alfred.agent import ToolEvent
from alfred.interfaces.webui.contracts import WebUISessionManager
from alfred.session import Message, Role, Session, SessionMeta, TextBlock, ToolCallRecord
from alfred.token_tracker import TokenTracker

DEFAULT_MODEL_NAME = "kimi/k2-test"
DEFAULT_CONTEXT_TOKENS = 321
DEFAULT_SESSION_USAGE: dict[str | None, dict[str, Any]] = {
    None: {
        "prompt_tokens": 11,
        "completion_tokens": 22,
        "prompt_tokens_details": {"cached_tokens": 3},
        "completion_tokens_details": {"reasoning_tokens": 4},
    },
    "session-2": {
        "prompt_tokens": 44,
        "completion_tokens": 55,
        "prompt_tokens_details": {"cached_tokens": 6},
        "completion_tokens_details": {"reasoning_tokens": 7},
    },
}
DEFAULT_CHAT_CHUNKS = ["Hello", "!", " How", " can", " I", " help", "?"]


class FakeSocketClient:
    """Socket client fake for runtime status tests."""

    def __init__(self, *, socket_path: Path | None = None, is_connected: bool = False) -> None:
        self.socket_path = socket_path or Path("/tmp/alfred/notify.sock")
        self.is_connected = is_connected


def make_tool_call(
    tool_call_id: str | None = None,
    *,
    tool_name: str = "read_file",
    arguments: dict[str, Any] | None = None,
    output: str = "",
    status: Literal["success", "error"] = "success",
    insert_position: int = 0,
    sequence: int = 0,
) -> ToolCallRecord:
    """Create a real ToolCallRecord."""

    return ToolCallRecord(
        tool_call_id=tool_call_id or f"tool-{uuid4().hex[:8]}",
        tool_name=tool_name,
        arguments=arguments or {},
        output=output,
        status=status,  # type: ignore[arg-type]
        insert_position=insert_position,
        sequence=sequence,
    )


def make_message(
    role: str | Role,
    content: str,
    *,
    idx: int = 0,
    id: str | None = None,
    timestamp: datetime | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    reasoning_tokens: int = 0,
    reasoning_content: str = "",
    text_blocks: list[dict[str, Any] | TextBlock] | None = None,
    tool_calls: list[ToolCallRecord] | None = None,
    streaming: bool = False,
) -> Message:
    """Create a real Message."""

    role_enum = role if isinstance(role, Role) else Role(role)
    converted_text_blocks: list[TextBlock] | None = None
    if text_blocks is not None:
        converted_text_blocks = []
        for block in text_blocks:
            if isinstance(block, TextBlock):
                converted_text_blocks.append(block)
            else:
                converted_text_blocks.append(
                    TextBlock(
                        content=block.get("content", ""),
                        sequence=block.get("sequence", 0),
                    )
                )

    return Message(
        idx=idx,
        role=role_enum,
        content=content,
        id=id,
        timestamp=timestamp or datetime.now(UTC),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        reasoning_tokens=reasoning_tokens,
        reasoning_content=reasoning_content,
        text_blocks=converted_text_blocks,
        tool_calls=tool_calls,
        streaming=streaming,
    )


def make_session_meta(
    session_id: str,
    *,
    created_at: datetime | None = None,
    last_active: datetime | None = None,
    status: Literal["active", "idle"] = "active",
    message_count: int = 0,
    summary: str = "Test session summary",
) -> SessionMeta:
    """Create a real SessionMeta and attach the optional summary used by UI tests."""

    now = created_at or datetime.now(UTC)
    meta = SessionMeta(
        session_id=session_id,
        created_at=now,
        last_active=last_active or now,
        status=status,  # type: ignore[arg-type]
        message_count=message_count,
    )
    meta.summary = summary  # type: ignore[attr-defined]
    return meta


def make_session(
    session_id: str,
    *,
    messages: list[Message] | None = None,
    status: Literal["active", "idle"] = "active",
    summary: str = "Test session summary",
) -> Session:
    """Create a real Session with Web UI-friendly metadata."""

    session_messages = list(messages or [])
    now = datetime.now(UTC)
    meta = make_session_meta(
        session_id,
        created_at=now,
        last_active=now,
        status=status,
        message_count=len(session_messages),
        summary=summary,
    )
    session = Session(meta=meta, messages=session_messages)
    session.summary = summary  # type: ignore[attr-defined]
    return session


@dataclass
class FakeCore:
    """Core stub exposing the session manager surface the server uses."""

    session_manager: WebUISessionManager

    @property
    def summarizer(self) -> Any | None:
        """Return None for tests that don't need summarizer."""
        return None


class FakeSessionManager:
    """Session manager fake for Web UI tests."""

    def __init__(self, sessions: list[Session] | None = None) -> None:
        if sessions is None:
            sessions = [
                make_session("session-1", messages=[make_message("user", "hello")]),
                make_session("session-2", messages=[make_message("user", "resumed")]),
            ]
            sessions[1].meta.last_active = sessions[0].meta.last_active - timedelta(seconds=1)
        self._sessions: dict[str, Session] = {session.meta.session_id: session for session in sessions}
        self._current_session_id: str | None = sessions[0].meta.session_id if sessions else None
        self.new_session_called = False
        self.resume_session_called = False
        self.list_sessions_called = False

    def _current_session(self) -> Session | None:
        if self._current_session_id is None:
            return None
        return self._sessions.get(self._current_session_id)

    def _next_session_id(self) -> str:
        return f"session-{len(self._sessions) + 1}"

    def has_active_session(self) -> bool:
        """Mirror the production session manager helper used by context display."""

        return self._current_session_id is not None

    def get_current_cli_session(self) -> Session | None:
        """Return the current CLI session."""

        return self._current_session()

    def get_session_messages(self, session_id: str | None = None) -> list[Message]:
        """Return session messages for context-style helpers."""

        session = self._current_session() if session_id is None else self._sessions.get(session_id)
        if session is None:
            return []
        return list(session.messages)

    def get_messages_for_context(self, session_id: str | None = None) -> list[tuple[str, str]]:
        """Return the simplified display shape used by context display helpers."""

        messages = self.get_session_messages(session_id)
        return [
            (
                message.role.value if hasattr(message.role, "value") else str(message.role),
                message.content,
            )
            for message in messages
        ]

    def start_session(self) -> Session:
        """Start a new session immediately."""

        session = make_session(self._next_session_id())
        self._sessions[session.meta.session_id] = session
        self._current_session_id = session.meta.session_id
        return session

    async def new_session_async(self) -> Session:
        """Create a new current session."""

        self.new_session_called = True
        return self.start_session()

    async def resume_session_async(self, session_id: str) -> Session:
        """Switch the current session to an existing session."""

        self.resume_session_called = True
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        self._current_session_id = session_id
        return session

    async def list_sessions_async(self) -> list[SessionMeta]:
        """List sessions in descending last-active order."""

        self.list_sessions_called = True
        sessions = sorted(
            self._sessions.values(),
            key=lambda session: session.meta.last_active,
            reverse=True,
        )
        metas: list[SessionMeta] = []
        for session in sessions:
            session.meta.summary = getattr(session, "summary", "")  # type: ignore[attr-defined]
            metas.append(session.meta)
        return metas

    def _find_message_index(self, session: Session, message_id: str) -> int:
        for index, message in enumerate(session.messages):
            if message.id == message_id:
                return index
        raise ValueError(f"Message {message_id} not found")

    async def truncate_after_message_async(self, message_id: str, session_id: str | None = None) -> Session:
        session = self._current_session() if session_id is None else self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id or self._current_session_id} not found")

        message_index = self._find_message_index(session, message_id)
        del session.messages[message_index + 1 :]
        session.meta.message_count = len(session.messages)
        session.meta.last_active = datetime.now(UTC)
        return session

    async def replace_message_and_truncate_after_async(
        self,
        message_id: str,
        content: str,
        session_id: str | None = None,
    ) -> Session:
        session = self._current_session() if session_id is None else self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id or self._current_session_id} not found")

        message_index = self._find_message_index(session, message_id)
        session.messages[message_index].content = content
        del session.messages[message_index + 1 :]
        session.meta.message_count = len(session.messages)
        session.meta.last_active = datetime.now(UTC)
        return session


class FakeContextLoader:
    """Context loader fake for Web UI tests."""

    def __init__(self) -> None:
        self.sections: dict[str, bool] = {}
        self.toggle_called_with: list[tuple[str, bool]] = []

    def toggle_section(self, section: str, enabled: bool) -> bool:
        """Toggle a context section on/off."""
        self.toggle_called_with.append((section, enabled))
        was_enabled = self.sections.get(section, True)
        self.sections[section] = enabled
        return was_enabled != enabled


class FakeAlfred:
    """Top-level Alfred fake for Web UI tests."""

    def __init__(
        self,
        *,
        chunks: list[str] | None = None,
        stream_parts: list[str | ToolEvent] | None = None,
        sessions: list[Session] | None = None,
        model_name: str = DEFAULT_MODEL_NAME,
        context_tokens: int = DEFAULT_CONTEXT_TOKENS,
        session_usage: dict[str | None, dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None,
        chunk_delay: float = 0.0,
    ) -> None:
        self.core = FakeCore(FakeSessionManager(sessions))
        self.token_tracker = TokenTracker()
        self.context_loader = FakeContextLoader()
        self.socket_client = FakeSocketClient()
        self._socket_client = self.socket_client
        self.model_name = model_name
        self.config = config or {"model": model_name}
        self._stream_parts = list(stream_parts or chunks or DEFAULT_CHAT_CHUNKS)
        self._session_usage = session_usage or DEFAULT_SESSION_USAGE
        self._context_tokens = context_tokens
        self._chunk_delay = chunk_delay
        self.synced_session_ids: list[str | None] = []
        self.chat_called = False
        self.chat_messages: list[str] = []
        self.last_message: str | None = None

    async def chat_stream(
        self,
        message: str,
        tool_callback: Callable[[ToolEvent], None] | None = None,
        session_id: str | None = None,
        persist_partial: bool = False,
        assistant_message_id: str | None = None,
        reuse_user_message: bool = False,
    ):
        """Yield the configured stream and emit configured tool events in order."""

        self.chat_called = True
        self.chat_messages.append(message)
        self.last_message = message
        self.token_tracker.add({"prompt_tokens": max(len(message) // 4, 1), "completion_tokens": 0})

        session_manager = self.core.session_manager
        session = session_manager.get_current_cli_session()
        if session is None:
            session = session_manager.start_session()

        assistant_msg = None
        if persist_partial:
            if not (reuse_user_message and session.messages and session.messages[-1].role is Role.USER):
                session.messages.append(make_message("user", message, idx=len(session.messages), id=f"user-{len(session.messages)}"))
            assistant_msg = make_message(
                "assistant",
                "",
                idx=len(session.messages),
                id=assistant_message_id or f"assistant-{len(session.messages)}",
                streaming=True,
            )
            session.messages.append(assistant_msg)
            session.meta.message_count = len(session.messages)
            session.meta.last_active = datetime.now(UTC)

        completion_tokens = 0
        for part in self._stream_parts:
            if isinstance(part, str):
                completion_tokens += len(part)
                if assistant_msg is not None:
                    assistant_msg.content += part
                if self._chunk_delay:
                    await asyncio.sleep(self._chunk_delay)
                yield part
            else:
                if tool_callback is not None:
                    tool_callback(part)

        if assistant_msg is not None:
            assistant_msg.streaming = False
            session.meta.last_active = datetime.now(UTC)
            session.meta.message_count = len(session.messages)

        self.token_tracker.add(
            {
                "prompt_tokens": 0,
                "completion_tokens": max(completion_tokens // 4, 1),
            }
        )
        return

    async def stop(self) -> None:
        """No-op shutdown hook for protocol compatibility."""

        return None

    @property
    def new_session_called(self) -> bool:
        return self.core.session_manager.new_session_called

    @property
    def resume_session_called(self) -> bool:
        return self.core.session_manager.resume_session_called

    @property
    def list_sessions_called(self) -> bool:
        return self.core.session_manager.list_sessions_called

    def sync_token_tracker_from_session(self, session_id: str | None = None) -> None:
        """Reset and seed the token tracker with deterministic totals."""

        self.synced_session_ids.append(session_id)
        self.token_tracker.reset()
        self.token_tracker.set_context_tokens(self._context_tokens)
        usage = self._session_usage.get(session_id, self._session_usage.get(None, {}))
        self.token_tracker.add(usage)
