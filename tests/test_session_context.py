"""Tests for session context integration using dependency injection."""

from pathlib import Path

import pytest

from alfred.session import SessionManager
from alfred.session_context import SessionContextBuilder
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


class TestSessionContextBuilder:
    """Tests for building context with session history."""

    def test_build_context_empty_session(self, session_manager: SessionManager):
        """Context includes system prompt even with empty session."""
        session_manager.start_session()

        builder = SessionContextBuilder(session_manager)
        context = builder.build_context("What time is it?")

        assert "## CONVERSATION HISTORY" in context
        assert "## CURRENT MESSAGE" in context
        assert "What time is it?" in context

    def test_build_context_with_history(self, session_manager: SessionManager):
        """Context includes session messages in order."""
        session_manager.start_session()
        session_manager.add_message("user", "Hello")
        session_manager.add_message("assistant", "Hi there")

        builder = SessionContextBuilder(session_manager)
        context = builder.build_context("How are you?")

        assert "User: Hello" in context
        assert "Assistant: Hi there" in context
        assert "## CURRENT MESSAGE" in context
        assert "How are you?" in context

    def test_build_context_message_format(self, session_manager: SessionManager):
        """Messages formatted as simple prefix."""
        session_manager.start_session()
        session_manager.add_message("user", "My question")
        session_manager.add_message("assistant", "My answer")

        builder = SessionContextBuilder(session_manager)
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

    def test_build_context_without_session_raises(self, session_manager: SessionManager):
        """Raises if no active session."""
        # Don't start a session
        builder = SessionContextBuilder(session_manager)

        with pytest.raises(RuntimeError, match="No active session"):
            builder.build_context("Hello")

    def test_system_messages_included(self, session_manager: SessionManager):
        """System messages included in context (for tool results)."""
        session_manager.start_session()
        session_manager.add_message("user", "Do something")
        session_manager.add_message("system", "Tool result: file created")
        session_manager.add_message("assistant", "Done")

        builder = SessionContextBuilder(session_manager)
        context = builder.build_context("Next")

        assert "System: Tool result: file created" in context

    def test_build_context_with_many_messages(self, session_manager: SessionManager):
        """Context includes all messages (no limit in PRD #54)."""
        session_manager.start_session()

        # Add 50 messages
        for i in range(25):
            session_manager.add_message("user", f"Message {i}")
            session_manager.add_message("assistant", f"Response {i}")

        builder = SessionContextBuilder(session_manager)
        context = builder.build_context("Final")

        # All messages should be present
        for i in range(25):
            assert f"User: Message {i}" in context
            assert f"Assistant: Response {i}" in context


class TestSessionContextAutoStart:
    """Tests for session auto-start on first message."""

    def test_auto_start_on_first_message(self, session_manager: SessionManager):
        """Session auto-starts when first message is added."""
        assert not session_manager.has_active_session()

        # Simulate what CLI does - add message triggers start
        if not session_manager.has_active_session():
            session_manager.start_session()
        session_manager.add_message("user", "First message")

        assert session_manager.has_active_session()
        assert len(session_manager.get_messages()) == 1
