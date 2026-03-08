"""Tests for session storage using dependency injection."""

from datetime import datetime
from pathlib import Path

import pytest

from alfred.session import Message, Role, Session, SessionManager, SessionMeta
from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory."""
    return tmp_path


@pytest.fixture
def sqlite_store(temp_data_dir: Path) -> SQLiteStore:
    """Create SQLiteStore for testing."""
    return SQLiteStore(temp_data_dir / "test.db")


@pytest.fixture
def session_manager(sqlite_store: SQLiteStore, temp_data_dir: Path) -> SessionManager:
    """Create SessionManager with injected dependencies."""
    return SessionManager(store=sqlite_store, data_dir=temp_data_dir)


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
        assert meta.message_count == 0


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
    """Tests for SessionManager with dependency injection."""

    def test_constructor_requires_store_and_data_dir(self, temp_data_dir: Path):
        """SessionManager requires store and data_dir in constructor."""
        store = SQLiteStore(temp_data_dir / "test.db")

        manager = SessionManager(store=store, data_dir=temp_data_dir)

        assert manager.store is store
        assert manager._data_dir == temp_data_dir

    def test_start_session_creates_new_session(
        self, session_manager: SessionManager
    ):
        """start_session creates a new session."""
        session = session_manager.start_session()

        assert isinstance(session, Session)
        assert session.meta.status == "active"
        assert session_manager.has_active_session()

    def test_start_session_clears_existing(
        self, session_manager: SessionManager
    ):
        """start_session clears any existing session."""
        session1 = session_manager.start_session()

        session2 = session_manager.start_session()

        assert session1.meta.session_id != session2.meta.session_id
        assert len(session2.messages) == 0

    def test_add_message_appends_to_session(
        self, session_manager: SessionManager
    ):
        """add_message appends message to current session."""
        session_manager.start_session()

        session_manager.add_message("user", "Hello")
        session_manager.add_message("assistant", "Hi")

        messages = session_manager.get_messages()
        assert len(messages) == 2
        assert messages[0].role == Role.USER
        assert messages[0].content == "Hello"
        assert messages[0].idx == 0
        assert messages[1].role == Role.ASSISTANT
        assert messages[1].content == "Hi"
        assert messages[1].idx == 1

    def test_add_message_updates_meta(
        self, session_manager: SessionManager
    ):
        """add_message updates session metadata."""
        session = session_manager.start_session()

        assert session.meta.message_count == 0

        session_manager.add_message("user", "Hello")

        assert session.meta.message_count == 1

    def test_add_message_without_session_raises(self, session_manager: SessionManager):
        """add_message raises if no session exists."""
        with pytest.raises(RuntimeError, match="No active session"):
            session_manager.add_message("user", "Hello")

    def test_get_messages_returns_all_in_order(
        self, session_manager: SessionManager
    ):
        """get_messages returns all messages chronologically."""
        session_manager.start_session()

        session_manager.add_message("user", "First")
        session_manager.add_message("assistant", "Second")
        session_manager.add_message("user", "Third")

        messages = session_manager.get_messages()
        assert len(messages) == 3
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"

    def test_get_messages_empty_session(
        self, session_manager: SessionManager
    ):
        """get_messages returns empty list for new session."""
        session_manager.start_session()

        messages = session_manager.get_messages()
        assert messages == []

    def test_clear_session_removes_session(
        self, session_manager: SessionManager
    ):
        """clear_session removes current session."""
        session_manager.start_session()
        session_manager.add_message("user", "Hello")

        session_manager.clear_session()

        assert not session_manager.has_active_session()
        with pytest.raises(RuntimeError, match="No active session"):
            session_manager.get_messages()

    def test_has_active_session(self, session_manager: SessionManager):
        """has_active_session returns correct state."""
        assert not session_manager.has_active_session()

        session_manager.start_session()
        assert session_manager.has_active_session()

        session_manager.clear_session()
        assert not session_manager.has_active_session()


class TestSessionManagerPersistence:
    """Tests for session persistence with SQLiteStore."""

    def test_session_persists_across_manager_instances(
        self, temp_data_dir: Path, sqlite_store: SQLiteStore
    ):
        """Sessions persist when creating new manager with same store."""
        # Create first manager and add messages
        manager1 = SessionManager(store=sqlite_store, data_dir=temp_data_dir)
        session = manager1.start_session()
        session_id = session.meta.session_id
        manager1.add_message("user", "Persistent message")

        # Create second manager with same store
        manager2 = SessionManager(store=sqlite_store, data_dir=temp_data_dir)
        loaded_session = manager2.get_or_create_session(session_id)

        assert len(loaded_session.messages) == 1
        assert loaded_session.messages[0].content == "Persistent message"

    def test_different_managers_are_independent(
        self, temp_data_dir: Path
    ):
        """Different store instances create isolated managers."""
        store1 = SQLiteStore(temp_data_dir / "db1.db")
        store2 = SQLiteStore(temp_data_dir / "db2.db")

        manager1 = SessionManager(store=store1, data_dir=temp_data_dir)
        manager2 = SessionManager(store=store2, data_dir=temp_data_dir)

        # Add to manager1
        session1 = manager1.start_session()
        manager1.add_message("user", "Manager 1 message")

        # Manager2 should not see it
        sessions = manager2.list_sessions()
        assert len(sessions) == 0
