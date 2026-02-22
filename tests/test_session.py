"""Tests for session storage (PRD #53)."""

import pytest
from datetime import datetime
from pathlib import Path
from uuid import UUID

from src.session import Message, Role, Session, SessionMeta, SessionManager
from src.session_storage import SessionStorage


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
        pass  # No-op in mock


@pytest.fixture
def mock_storage(tmp_path: Path) -> MockStorage:
    """Create mock storage."""
    return MockStorage(tmp_path)


@pytest.fixture
def initialized_manager(mock_storage: MockStorage):
    """Create initialized SessionManager."""
    # Reset singleton state
    SessionManager._instance = None
    SessionManager._storage = None
    SessionManager._sessions = {}
    SessionManager._cli_session_id = None

    SessionManager.initialize(mock_storage)
    manager = SessionManager.get_instance()
    yield manager

    # Cleanup
    SessionManager._instance = None
    SessionManager._storage = None
    SessionManager._sessions = {}
    SessionManager._cli_session_id = None


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Can create a message with idx, role and content."""
        msg = Message(idx=0, role=Role.USER, content="Hello")

        assert msg.idx == 0
        assert msg.role == Role.USER
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)
        assert msg.embedding is None

    def test_message_roles(self):
        """Message supports user, assistant, and system roles."""
        user_msg = Message(idx=0, role=Role.USER, content="Hi")
        assistant_msg = Message(idx=1, role=Role.ASSISTANT, content="Hello")
        system_msg = Message(idx=2, role=Role.SYSTEM, content="System prompt")

        assert user_msg.role == Role.USER
        assert assistant_msg.role == Role.ASSISTANT
        assert system_msg.role == Role.SYSTEM

    def test_message_with_embedding(self):
        """Message can have an embedding."""
        msg = Message(idx=0, role=Role.USER, content="Hello", embedding=[0.1, 0.2, 0.3])

        assert msg.embedding == [0.1, 0.2, 0.3]


class TestSessionMeta:
    """Tests for SessionMeta dataclass."""

    def test_meta_creation(self):
        """Can create session metadata."""
        now = datetime.now()
        meta = SessionMeta(
            session_id="test123",
            created_at=now,
            last_active=now,
            status="active",
        )

        assert meta.session_id == "test123"
        assert meta.created_at == now
        assert meta.last_active == now
        assert meta.status == "active"
        assert meta.current_count == 0
        assert meta.archive_count == 0

    def test_message_count_property(self):
        """message_count returns sum of current and archive."""
        now = datetime.now()
        meta = SessionMeta(
            session_id="test123",
            created_at=now,
            last_active=now,
            status="active",
            current_count=10,
            archive_count=5,
        )

        assert meta.message_count == 15


class TestSession:
    """Tests for Session dataclass."""

    def test_session_creation(self):
        """Can create a session with metadata."""
        now = datetime.now()
        meta = SessionMeta(
            session_id="test123",
            created_at=now,
            last_active=now,
            status="active",
        )
        session = Session(meta=meta)

        assert session.meta.session_id == "test123"
        assert session.messages == []

    def test_session_with_messages(self):
        """Session can hold messages."""
        now = datetime.now()
        meta = SessionMeta(
            session_id="test123",
            created_at=now,
            last_active=now,
            status="active",
        )
        session = Session(meta=meta)
        msg1 = Message(idx=0, role=Role.USER, content="Hello")
        msg2 = Message(idx=1, role=Role.ASSISTANT, content="Hi there")

        session.messages.append(msg1)
        session.messages.append(msg2)

        assert len(session.messages) == 2
        assert session.messages[0].content == "Hello"
        assert session.messages[1].content == "Hi there"


class TestSessionManager:
    """Tests for SessionManager singleton."""

    def test_singleton_pattern(self, initialized_manager: SessionManager):
        """SessionManager is a singleton."""
        manager2 = SessionManager.get_instance()
        assert initialized_manager is manager2

    def test_start_session_creates_new_session(
        self, initialized_manager: SessionManager, mock_storage: MockStorage
    ):
        """start_session creates a new session."""
        session = initialized_manager.start_session()

        assert isinstance(session, Session)
        assert session.meta.status == "active"
        assert initialized_manager.has_active_session()

    def test_start_session_clears_existing(
        self, initialized_manager: SessionManager, mock_storage: MockStorage
    ):
        """start_session clears any existing session."""
        session1 = initialized_manager.start_session()
        session1_id = session1.meta.session_id

        session2 = initialized_manager.start_session()

        assert session1.meta.session_id != session2.meta.session_id
        assert len(session2.messages) == 0

    def test_add_message_appends_to_session(
        self, initialized_manager: SessionManager, mock_storage: MockStorage
    ):
        """add_message appends message to current session."""
        initialized_manager.start_session()

        initialized_manager.add_message("user", "Hello")
        initialized_manager.add_message("assistant", "Hi")

        messages = initialized_manager.get_messages()
        assert len(messages) == 2
        assert messages[0].role == Role.USER
        assert messages[0].content == "Hello"
        assert messages[0].idx == 0
        assert messages[1].role == Role.ASSISTANT
        assert messages[1].content == "Hi"
        assert messages[1].idx == 1

    def test_add_message_updates_meta(
        self, initialized_manager: SessionManager, mock_storage: MockStorage
    ):
        """add_message updates session metadata."""
        session = initialized_manager.start_session()

        assert session.meta.current_count == 0

        initialized_manager.add_message("user", "Hello")

        assert session.meta.current_count == 1

    def test_add_message_without_session_raises(self, initialized_manager: SessionManager):
        """add_message raises if no session exists."""
        with pytest.raises(RuntimeError, match="No active session"):
            initialized_manager.add_message("user", "Hello")

    def test_get_messages_returns_all_in_order(
        self, initialized_manager: SessionManager, mock_storage: MockStorage
    ):
        """get_messages returns all messages chronologically."""
        initialized_manager.start_session()

        initialized_manager.add_message("user", "First")
        initialized_manager.add_message("assistant", "Second")
        initialized_manager.add_message("user", "Third")

        messages = initialized_manager.get_messages()
        assert len(messages) == 3
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"

    def test_get_messages_empty_session(
        self, initialized_manager: SessionManager, mock_storage: MockStorage
    ):
        """get_messages returns empty list for new session."""
        initialized_manager.start_session()

        messages = initialized_manager.get_messages()
        assert messages == []

    def test_clear_session_removes_session(
        self, initialized_manager: SessionManager, mock_storage: MockStorage
    ):
        """clear_session removes current session."""
        initialized_manager.start_session()
        initialized_manager.add_message("user", "Hello")

        initialized_manager.clear_session()

        assert not initialized_manager.has_active_session()
        with pytest.raises(RuntimeError, match="No active session"):
            initialized_manager.get_messages()

    def test_has_active_session(self, initialized_manager: SessionManager):
        """has_active_session returns correct state."""
        assert not initialized_manager.has_active_session()

        initialized_manager.start_session()
        assert initialized_manager.has_active_session()

        initialized_manager.clear_session()
        assert not initialized_manager.has_active_session()


class TestSessionManagerIsolation:
    """Tests for session isolation between instances."""

    def test_singleton_shares_state(
        self, initialized_manager: SessionManager, mock_storage: MockStorage
    ):
        """All instances share the same session state."""
        initialized_manager.start_session()
        initialized_manager.add_message("user", "Shared message")

        manager2 = SessionManager.get_instance()
        messages = manager2.get_messages()

        assert len(messages) == 1
        assert messages[0].content == "Shared message"
