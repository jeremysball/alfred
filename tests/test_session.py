"""Tests for session storage (PRD #54)."""

import pytest
from datetime import datetime
from uuid import UUID

from src.session import Message, Role, Session, SessionManager


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Can create a message with role and content."""
        msg = Message(role=Role.USER, content="Hello")
        
        assert msg.role == Role.USER
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)

    def test_message_roles(self):
        """Message supports user, assistant, and system roles."""
        user_msg = Message(role=Role.USER, content="Hi")
        assistant_msg = Message(role=Role.ASSISTANT, content="Hello")
        system_msg = Message(role=Role.SYSTEM, content="System prompt")
        
        assert user_msg.role == Role.USER
        assert assistant_msg.role == Role.ASSISTANT
        assert system_msg.role == Role.SYSTEM


class TestSession:
    """Tests for Session dataclass."""

    def test_session_creation(self):
        """Can create a session with unique ID."""
        session = Session()
        
        assert isinstance(session.session_id, str)
        # Should be valid UUID
        UUID(session.session_id)
        assert isinstance(session.created_at, datetime)
        assert session.messages == []

    def test_session_with_messages(self):
        """Session can hold messages."""
        session = Session()
        msg1 = Message(role=Role.USER, content="Hello")
        msg2 = Message(role=Role.ASSISTANT, content="Hi there")
        
        session.messages.append(msg1)
        session.messages.append(msg2)
        
        assert len(session.messages) == 2
        assert session.messages[0].content == "Hello"
        assert session.messages[1].content == "Hi there"


class TestSessionManager:
    """Tests for SessionManager singleton."""

    def test_singleton_pattern(self):
        """SessionManager is a singleton."""
        manager1 = SessionManager.get_instance()
        manager2 = SessionManager.get_instance()
        
        assert manager1 is manager2

    def test_start_session_creates_new_session(self):
        """start_session creates a new session."""
        manager = SessionManager.get_instance()
        manager.clear_session()  # Clean state
        
        session = manager.start_session()
        
        assert isinstance(session, Session)
        assert manager._session is session

    def test_start_session_clears_existing(self):
        """start_session clears any existing session."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        
        session1 = manager.start_session()
        session1.messages.append(Message(role=Role.USER, content="Old"))
        
        session2 = manager.start_session()
        
        assert session1 is not session2
        assert len(session2.messages) == 0

    def test_add_message_appends_to_session(self):
        """add_message appends message to current session."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        
        manager.add_message("user", "Hello")
        manager.add_message("assistant", "Hi")
        
        messages = manager.get_messages()
        assert len(messages) == 2
        assert messages[0].role == Role.USER
        assert messages[0].content == "Hello"
        assert messages[1].role == Role.ASSISTANT
        assert messages[1].content == "Hi"

    def test_add_message_without_session_raises(self):
        """add_message raises if no session exists."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        
        with pytest.raises(RuntimeError, match="No active session"):
            manager.add_message("user", "Hello")

    def test_get_messages_returns_all_in_order(self):
        """get_messages returns all messages chronologically."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        
        manager.add_message("user", "First")
        manager.add_message("assistant", "Second")
        manager.add_message("user", "Third")
        
        messages = manager.get_messages()
        assert len(messages) == 3
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"

    def test_get_messages_empty_session(self):
        """get_messages returns empty list for new session."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        
        messages = manager.get_messages()
        assert messages == []

    def test_clear_session_removes_session(self):
        """clear_session removes current session."""
        manager = SessionManager.get_instance()
        manager.start_session()
        manager.add_message("user", "Hello")
        
        manager.clear_session()
        
        assert manager._session is None
        with pytest.raises(RuntimeError, match="No active session"):
            manager.get_messages()

    def test_has_active_session(self):
        """has_active_session returns correct state."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        
        assert not manager.has_active_session()
        
        manager.start_session()
        assert manager.has_active_session()
        
        manager.clear_session()
        assert not manager.has_active_session()


class TestSessionManagerIsolation:
    """Tests for session isolation between instances."""

    def test_singleton_shares_state(self):
        """All instances share the same session state."""
        manager1 = SessionManager.get_instance()
        manager1.clear_session()
        manager1.start_session()
        manager1.add_message("user", "Shared message")
        
        manager2 = SessionManager.get_instance()
        messages = manager2.get_messages()
        
        assert len(messages) == 1
        assert messages[0].content == "Shared message"
