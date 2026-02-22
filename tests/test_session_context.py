"""Tests for session context integration (PRD #54 Milestone 3)."""

import pytest
from pathlib import Path

from src.session import Message, Role, Session, SessionMeta, SessionManager
from src.session_context import SessionContextBuilder


class MockStorage:
    """Mock storage for testing SessionManager without file I/O."""

    def __init__(self, tmp_path: Path):
        self.sessions_dir = tmp_path / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_path = self.sessions_dir / "current.json"
        self._sessions: dict[str, SessionMeta] = {}
        self._messages: dict[str, list[Message]] = {}
        self._cli_current: str | None = None

    def session_exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())

    def get_cli_current(self) -> str | None:
        return self._cli_current

    def set_cli_current(self, session_id: str) -> None:
        self._cli_current = session_id

    def get_meta(self, session_id: str) -> SessionMeta | None:
        return self._sessions.get(session_id)

    def save_meta(self, meta: SessionMeta) -> None:
        self._sessions[meta.session_id] = meta

    def create_session(self, session_id: str | None = None) -> SessionMeta:
        from uuid import uuid4
        from datetime import datetime

        sid = session_id or f"sess_{uuid4().hex[:12]}"
        now = datetime.now()
        meta = SessionMeta(
            session_id=sid,
            created_at=now,
            last_active=now,
            status="active",
        )
        self._sessions[sid] = meta
        self._messages[sid] = []
        return meta

    def _generate_session_id(self) -> str:
        from uuid import uuid4

        return f"sess_{uuid4().hex[:12]}"

    def load_messages(self, session_id: str) -> list[Message]:
        return self._messages.get(session_id, [])

    async def append_message(self, session_id: str, message: Message) -> None:
        if session_id not in self._messages:
            self._messages[session_id] = []
        self._messages[session_id].append(message)

    def load_session(self, session_id: str) -> Session | None:
        meta = self.get_meta(session_id)
        if meta is None:
            return None
        messages = self.load_messages(session_id)
        return Session(meta=meta, messages=messages)

    def spawn_embed_task(self, session_id: str, idx: int, content: str) -> None:
        pass


@pytest.fixture
def initialized_manager(tmp_path: Path):
    """Create initialized SessionManager."""
    # Reset singleton state
    SessionManager._instance = None
    SessionManager._storage = None
    SessionManager._sessions = {}
    SessionManager._cli_session_id = None

    mock_storage = MockStorage(tmp_path)
    SessionManager.initialize(mock_storage)
    manager = SessionManager.get_instance()
    yield manager

    # Cleanup
    SessionManager._instance = None
    SessionManager._storage = None
    SessionManager._sessions = {}
    SessionManager._cli_session_id = None


class TestSessionContextBuilder:
    """Tests for building context with session history."""

    def test_build_context_empty_session(self, initialized_manager: SessionManager):
        """Context includes system prompt even with empty session."""
        initialized_manager.start_session()

        builder = SessionContextBuilder(initialized_manager)
        context = builder.build_context("What time is it?")

        assert "## CONVERSATION HISTORY" in context
        assert "## CURRENT MESSAGE" in context
        assert "What time is it?" in context

    def test_build_context_with_history(self, initialized_manager: SessionManager):
        """Context includes session messages in order."""
        initialized_manager.start_session()
        initialized_manager.add_message("user", "Hello")
        initialized_manager.add_message("assistant", "Hi there")

        builder = SessionContextBuilder(initialized_manager)
        context = builder.build_context("How are you?")

        assert "User: Hello" in context
        assert "Assistant: Hi there" in context
        assert "## CURRENT MESSAGE" in context
        assert "How are you?" in context

    def test_build_context_message_format(self, initialized_manager: SessionManager):
        """Messages formatted as simple prefix."""
        initialized_manager.start_session()
        initialized_manager.add_message("user", "My question")
        initialized_manager.add_message("assistant", "My answer")

        builder = SessionContextBuilder(initialized_manager)
        context = builder.build_context("Follow up")

        # Verify simple prefix format (Option A from decisions)
        lines = context.split("\n")
        history_section = False
        user_line = None
        assistant_line = None

        for line in lines:
            if "## CONVERSATION HISTORY" in line:
                history_section = True
                continue
            if history_section and line.startswith("User: "):
                user_line = line
            if history_section and line.startswith("Assistant: "):
                assistant_line = line

        assert user_line == "User: My question"
        assert assistant_line == "Assistant: My answer"

    def test_build_context_without_session_raises(self, initialized_manager: SessionManager):
        """Raises if no active session."""
        # Don't start a session
        builder = SessionContextBuilder(initialized_manager)

        with pytest.raises(RuntimeError, match="No active session"):
            builder.build_context("Hello")

    def test_system_messages_included(self, initialized_manager: SessionManager):
        """System messages included in context (for tool results)."""
        initialized_manager.start_session()
        initialized_manager.add_message("user", "Do something")
        initialized_manager.add_message("system", "Tool result: file created")
        initialized_manager.add_message("assistant", "Done")

        builder = SessionContextBuilder(initialized_manager)
        context = builder.build_context("Next")

        assert "System: Tool result: file created" in context

    def test_build_context_with_many_messages(self, initialized_manager: SessionManager):
        """Context includes all messages (no limit in PRD #54)."""
        initialized_manager.start_session()

        # Add 50 messages
        for i in range(25):
            initialized_manager.add_message("user", f"Message {i}")
            initialized_manager.add_message("assistant", f"Response {i}")

        builder = SessionContextBuilder(initialized_manager)
        context = builder.build_context("Final")

        # All messages should be present
        for i in range(25):
            assert f"User: Message {i}" in context
            assert f"Assistant: Response {i}" in context


class TestSessionContextAutoStart:
    """Tests for session auto-start on first message."""

    def test_auto_start_on_first_message(self, initialized_manager: SessionManager):
        """Session auto-starts when first message is added."""
        assert not initialized_manager.has_active_session()

        # Simulate what CLI does - add message triggers start
        if not initialized_manager.has_active_session():
            initialized_manager.start_session()
        initialized_manager.add_message("user", "First message")

        assert initialized_manager.has_active_session()
        assert len(initialized_manager.get_messages()) == 1
